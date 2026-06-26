import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from sse_starlette.sse import EventSourceResponse

from .schemas.models import AssistRequest, AssistResponse, AskRequest, Problem
from .config import CAPTURE_INTERVAL, CHANGE_THRESHOLD, LLM_PROVIDER
from screen_capture.change_detector import start_monitor
from screen_capture.problem_fetcher import fetch_problem_by_url


if LLM_PROVIDER == "openai":
    from .llm.openai_client import OpenAIClient
    llm = OpenAIClient()
elif LLM_PROVIDER == "local":
    from .llm.local_client import LocalClient
    llm = LocalClient()
else:
    from .llm.gemini_client import GeminiClient
    llm = GeminiClient()


CACHE_FILE = Path("poc/output/extracted_problem.json")
problem_cache: dict = {}
response_cache: dict = {}


def save_problem(result: dict) -> None:
    problem_cache.clear()
    problem_cache.update(result)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_cache() -> None:
    if not CACHE_FILE.exists():
        return
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if data.get("is_coding_problem"):
            problem_cache.update(data)
            print(f"cache loaded: {data.get('title', '-')}")
    except Exception as e:
        print(f"cache load error: {e}")


load_cache()


async def on_problem_change():
    try:
        result = await fetch_problem_by_url()
        title = result.get("title", "")
        if not result.get("is_coding_problem") or not title:
            return
        save_problem(result)
        response_cache.clear()
        print(f"problem updated: {title}")
    except Exception as e:
        print(f"fetch error: {e}")


async def on_title_change(title: str):
    if title and title != problem_cache.get("title", ""):
        problem_cache["title"] = title
        print(f"title updated: {title}")
        await on_problem_change()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        start_monitor(on_problem_change, on_title_change, CAPTURE_INTERVAL, CHANGE_THRESHOLD)
    )
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


async def resolve_problem(req_problem: Optional[Problem] = None) -> Problem:
    if req_problem:
        return req_problem
    if problem_cache:
        return Problem(**problem_cache)
    try:
        result = await fetch_problem_by_url()
        if result.get("is_coding_problem"):
            save_problem(result)
            return Problem(**problem_cache)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    raise HTTPException(status_code=404, detail="no problem detected")


def cached_response(key: str, content: str) -> AssistResponse:
    response_cache[key] = content
    return AssistResponse(content=content, provider=LLM_PROVIDER)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def get_status():
    return {
        "title": problem_cache.get("title", ""),
        "has_problem": bool(problem_cache),
    }


@app.get("/extract")
async def get_current_problem():
    if problem_cache:
        return problem_cache
    try:
        result = await fetch_problem_by_url()
        if result.get("is_coding_problem"):
            save_problem(result)
        return problem_cache if problem_cache else result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/hint", response_model=AssistResponse)
async def get_hint(req: AssistRequest):
    if "hint" in response_cache:
        return AssistResponse(content=response_cache["hint"], provider=LLM_PROVIDER)
    problem = await resolve_problem(req.problem)
    return cached_response("hint", await llm.get_hint(problem))


@app.post("/approach", response_model=AssistResponse)
async def get_approach(req: AssistRequest):
    if "approach" in response_cache:
        return AssistResponse(content=response_cache["approach"], provider=LLM_PROVIDER)
    problem = await resolve_problem(req.problem)
    return cached_response("approach", await llm.get_approach(problem))


@app.post("/solution", response_model=AssistResponse)
async def get_solution(req: AssistRequest):
    if "solution" in response_cache:
        return AssistResponse(content=response_cache["solution"], provider=LLM_PROVIDER)
    problem = await resolve_problem(req.problem)
    return cached_response("solution", await llm.get_solution(problem))


@app.post("/ask", response_model=AssistResponse)
async def ask(req: AskRequest):
    problem = await resolve_problem(req.problem)
    content = await llm.ask(problem, req.question, req.context or "")
    return AssistResponse(content=content, provider=LLM_PROVIDER)


def _stream_with_cache(cache_key: str, generator):
    """스트리밍하면서 동시에 캐시에 저장"""
    async def gen():
        if cache_key in response_cache:
            yield {"data": response_cache[cache_key]}
            return
        full = ""
        async for chunk in generator:
            full += chunk
            yield {"data": chunk}
        response_cache[cache_key] = full
    return EventSourceResponse(gen())


@app.post("/hint/stream")
async def stream_hint(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    return _stream_with_cache("hint", llm.stream_hint(problem))


@app.post("/approach/stream")
async def stream_approach(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    return _stream_with_cache("approach", llm.stream_approach(problem))


@app.post("/solution/stream")
async def stream_solution(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    return _stream_with_cache("solution", llm.stream_solution(problem))


@app.post("/ask/stream")
async def stream_ask(req: AskRequest):
    problem = await resolve_problem(req.problem)
    async def gen():
        async for chunk in llm.stream_ask(problem, req.question, req.context or ""):
            yield {"data": chunk}
    return EventSourceResponse(gen())

@app.post("/prefetch")
async def prefetch(req: AssistRequest):
    """문제 감지 시 hint/approach/solution 미리 생성해 캐시에 저장"""
    problem = await resolve_problem(req.problem)
    results = await asyncio.gather(
        llm.get_hint(problem),
        llm.get_approach(problem),
        llm.get_solution(problem),
        return_exceptions=True
    )
    keys = ["hint", "approach", "solution"]
    for key, result in zip(keys, results):
        if not isinstance(result, Exception):
            response_cache[key] = result
    return {"status": "ok", "cached": [k for k, r in zip(keys, results) if not isinstance(r, Exception)]}
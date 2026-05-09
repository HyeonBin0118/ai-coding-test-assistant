import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from .schemas.models import AssistRequest, AssistResponse, AskRequest, Problem
from .config import CAPTURE_INTERVAL, CHANGE_THRESHOLD, LLM_PROVIDER
from screen_capture.capture import capture_left_half
from screen_capture.extractor import extract_problem
from screen_capture.change_detector import start_monitor

if LLM_PROVIDER == "openai":
    from .llm.openai_client import OpenAIClient
    llm = OpenAIClient()
else:
    from .llm.gemini_client import GeminiClient
    llm = GeminiClient()

problem_cache: dict = {}
CACHE_FILE = Path("poc/output/extracted_problem.json")


def _load_cache():
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("is_coding_problem"):
                problem_cache.update(data)
                print(f"cache loaded: {data.get('title', '-')}")
        except Exception as e:
            print(f"cache load error: {e}")


_load_cache()


async def on_problem_change(img):
    try:
        result = await extract_problem(img)
        if result.get("is_coding_problem"):
            problem_cache.clear()
            problem_cache.update(result)
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"problem updated: {result.get('title', '-')}")
    except Exception as e:
        if "429" not in str(e):
            print(f"extract error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        start_monitor(on_problem_change, CAPTURE_INTERVAL, CHANGE_THRESHOLD)
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
        img = capture_left_half()
        result = await extract_problem(img)
        if result.get("is_coding_problem"):
            problem_cache.update(result)
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return Problem(**problem_cache)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    raise HTTPException(status_code=404, detail="no problem detected")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/extract")
async def get_current_problem():
    if problem_cache:
        return problem_cache
    try:
        img = capture_left_half()
        result = await extract_problem(img)
        if result.get("is_coding_problem"):
            problem_cache.update(result)
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        return problem_cache if problem_cache else result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


from sse_starlette.sse import EventSourceResponse


@app.post("/hint/stream")
async def stream_hint(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    async def generate():
        async for chunk in llm.stream_hint(problem):
            yield {"data": chunk}
    return EventSourceResponse(generate())


@app.post("/approach/stream")
async def stream_approach(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    async def generate():
        async for chunk in llm.stream_approach(problem):
            yield {"data": chunk}
    return EventSourceResponse(generate())


@app.post("/solution/stream")
async def stream_solution(req: AssistRequest):
    problem = await resolve_problem(req.problem)
    async def generate():
        async for chunk in llm.stream_solution(problem):
            yield {"data": chunk}
    return EventSourceResponse(generate())


@app.post("/ask/stream")
async def stream_ask(req: AskRequest):
    problem = await resolve_problem(req.problem)
    async def generate():
        async for chunk in llm.stream_ask(problem, req.question, req.context or ""):
            yield {"data": chunk}
    return EventSourceResponse(generate())
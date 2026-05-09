import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from .schemas.models import AssistRequest, AssistResponse, AskRequest, Problem
from .llm.gemini_client import GeminiClient
from .config import CAPTURE_INTERVAL, CHANGE_THRESHOLD
from screen_capture.capture import capture_left_half
from screen_capture.extractor import extract_problem
from screen_capture.change_detector import start_monitor

llm = GeminiClient()
problem_cache: dict = {}


async def on_problem_change(img):
    try:
        result = await extract_problem(img)
        if result.get("is_coding_problem"):
            problem_cache.clear()
            problem_cache.update(result)
            print(f"problem updated: {result.get('title', '-')}")
    except Exception as e:
        print(f"extract error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        start_monitor(on_problem_change, CAPTURE_INTERVAL, CHANGE_THRESHOLD)
    )
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


def resolve_problem(req_problem: Optional[Problem] = None) -> Problem:
    if req_problem:
        return req_problem
    if problem_cache:
        return Problem(**problem_cache)
    raise HTTPException(status_code=404, detail="no problem detected yet")

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/extract")
async def get_current_problem():
    if not problem_cache:
        img = capture_left_half()
        result = await extract_problem(img)
        if result.get("is_coding_problem"):
            problem_cache.update(result)
        return result
    return problem_cache


@app.post("/hint", response_model=AssistResponse)
async def get_hint(req: AssistRequest):
    problem = resolve_problem(req.problem)
    content = await llm.get_hint(problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/approach", response_model=AssistResponse)
async def get_approach(req: AssistRequest):
    problem = resolve_problem(req.problem)
    content = await llm.get_approach(problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/solution", response_model=AssistResponse)
async def get_solution(req: AssistRequest):
    problem = resolve_problem(req.problem)
    content = await llm.get_solution(problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/ask", response_model=AssistResponse)
async def ask(req: AskRequest):
    problem = resolve_problem(req.problem)
    content = await llm.ask(problem, req.question, req.context or "")
    return AssistResponse(content=content, provider="gemini")
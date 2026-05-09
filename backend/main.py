from fastapi import FastAPI
from .schemas.models import AssistRequest, AssistResponse, AskRequest
from .llm.gemini_client import GeminiClient

app = FastAPI()
client = GeminiClient()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/hint", response_model=AssistResponse)
async def get_hint(req: AssistRequest):
    content = await client.get_hint(req.problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/approach", response_model=AssistResponse)
async def get_approach(req: AssistRequest):
    content = await client.get_approach(req.problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/solution", response_model=AssistResponse)
async def get_solution(req: AssistRequest):
    content = await client.get_solution(req.problem)
    return AssistResponse(content=content, provider="gemini")


@app.post("/ask", response_model=AssistResponse)
async def ask(req: AskRequest):
    content = await client.ask(req.problem, req.question, req.context or "")
    return AssistResponse(content=content, provider="gemini")
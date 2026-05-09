from fastapi import APIRouter
from ..schemas.models import AssistRequest, AssistResponse
from ..llm.gemini_client import GeminiClient

router = APIRouter()
client = GeminiClient()


@router.post("/hint", response_model=AssistResponse)
async def get_hint(req: AssistRequest):
    content = await client.get_hint(req.problem)
    return AssistResponse(content=content, provider="gemini")
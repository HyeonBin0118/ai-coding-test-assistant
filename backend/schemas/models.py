from pydantic import BaseModel
from typing import Optional


class Problem(BaseModel):
    title: str
    description: str
    constraints: str
    examples: list[dict]


class AskRequest(BaseModel):
    problem: Problem
    question: str
    context: Optional[str] = None  # 이전 대화 맥락


class AssistRequest(BaseModel):
    problem: Problem


class AssistResponse(BaseModel):
    content: str
    provider: str
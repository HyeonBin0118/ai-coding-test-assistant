from pydantic import BaseModel
from typing import Optional


class Problem(BaseModel):
    title: str
    description: str
    constraints: str
    examples: list[dict]


class AssistRequest(BaseModel):
    problem: Optional[Problem] = None


class AskRequest(BaseModel):
    problem: Optional[Problem] = None
    question: str
    context: Optional[str] = None


class AssistResponse(BaseModel):
    content: str
    provider: str
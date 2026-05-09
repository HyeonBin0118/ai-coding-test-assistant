import re
import httpx
from ..schemas.models import Problem
from ..config import GEMINI_API_KEY
from .base import BaseLLMClient

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

HINT_PROMPT = """
다음 코딩 문제에 대한 힌트를 제공하세요.

규칙:
- 구체적인 알고리즘 이름이나 자료구조 이름을 직접 말하지 마세요
- 코드를 작성하지 마세요
- 문제를 어떤 관점으로 바라볼지 방향만 제시하세요
- 2~3문장 이내로 짧게

문제: {title}
설명: {description}
제한사항: {constraints}
"""

APPROACH_PROMPT = """
다음 코딩 문제의 풀이 접근법을 설명하세요.

규칙:
- 사용할 알고리즘과 자료구조를 명시하세요
- 풀이 흐름을 단계별로 설명하세요
- 코드는 작성하지 마세요
- 시간복잡도를 언급하세요

문제: {title}
설명: {description}
제한사항: {constraints}
"""

SOLUTION_PROMPT = """
다음 코딩 문제의 Python 정답 코드를 작성하세요.

- 정답 코드를 작성하세요
- 핵심 로직에 주석을 달아주세요
- 코드 아래에 간단한 풀이 설명을 추가하세요

문제: {title}
설명: {description}
제한사항: {constraints}
예제: {examples}
"""

ASK_PROMPT = """
다음 코딩 문제와 관련된 질문에 답변하세요.

문제: {title}
설명: {description}
제한사항: {constraints}

{context}
질문: {question}
"""


class GeminiClient(BaseLLMClient):

    async def _call(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()

        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    def _build_prompt(self, template: str, problem: Problem, **kwargs) -> str:
        return template.format(
            title=problem.title,
            description=problem.description,
            constraints=problem.constraints,
            examples=problem.examples,
            **kwargs,
        )

    async def get_hint(self, problem: Problem) -> str:
        prompt = self._build_prompt(HINT_PROMPT, problem)
        return await self._call(prompt)

    async def get_approach(self, problem: Problem) -> str:
        prompt = self._build_prompt(APPROACH_PROMPT, problem)
        return await self._call(prompt)

    async def get_solution(self, problem: Problem) -> str:
        prompt = self._build_prompt(SOLUTION_PROMPT, problem)
        return await self._call(prompt)

    async def ask(self, problem: Problem, question: str, context: str = "") -> str:
        ctx = f"이전 대화:\n{context}\n\n" if context else ""
        prompt = self._build_prompt(ASK_PROMPT, problem, question=question, context=ctx)
        return await self._call(prompt)
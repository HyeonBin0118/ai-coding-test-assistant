from openai import AsyncOpenAI
from ..schemas.models import Problem
from .base import BaseLLMClient
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

HINT_PROMPT = """다음 코딩 문제에 대한 힌트를 제공하세요.
규칙:
- 구체적인 알고리즘 이름이나 자료구조 이름을 직접 말하지 마세요
- 코드를 작성하지 마세요
- 문제를 어떤 관점으로 바라볼지 방향만 제시하세요
- 2~3문장 이내로 짧게

문제: {title}
설명: {description}
제한사항: {constraints}"""

APPROACH_PROMPT = """다음 코딩 문제의 풀이 접근법을 설명하세요.
규칙:
- 사용할 알고리즘과 자료구조를 명시하세요
- 풀이 흐름을 단계별로 설명하세요
- 코드는 작성하지 마세요
- 시간복잡도를 언급하세요

문제: {title}
설명: {description}
제한사항: {constraints}"""

SOLUTION_PROMPT = """다음 코딩 문제의 Python 정답 코드를 작성하세요.
- 정답 코드를 작성하세요
- 핵심 로직에 주석을 달아주세요
- 코드 아래에 간단한 풀이 설명을 추가하세요

문제: {title}
설명: {description}
제한사항: {constraints}
예제: {examples}"""

ASK_PROMPT = """다음 코딩 문제와 관련된 질문에 답변하세요.

문제: {title}
설명: {description}
제한사항: {constraints}

{context}질문: {question}"""


class OpenAIClient(BaseLLMClient):

    async def _call(self, prompt: str) -> str:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    def _build_prompt(self, template: str, problem: Problem, **kwargs) -> str:
        return template.format(
            title=problem.title,
            description=problem.description,
            constraints=problem.constraints,
            examples=problem.examples,
            **kwargs,
        )

    async def get_hint(self, problem: Problem) -> str:
        return await self._call(self._build_prompt(HINT_PROMPT, problem))

    async def get_approach(self, problem: Problem) -> str:
        return await self._call(self._build_prompt(APPROACH_PROMPT, problem))

    async def get_solution(self, problem: Problem) -> str:
        return await self._call(self._build_prompt(SOLUTION_PROMPT, problem))

    async def ask(self, problem: Problem, question: str, context: str = "") -> str:
        ctx = f"이전 대화:\n{context}\n\n" if context else ""
        return await self._call(self._build_prompt(ASK_PROMPT, problem, question=question, context=ctx))

    async def stream(self, prompt: str):
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3,
            stream=True,
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def stream_hint(self, problem: Problem):
        async for chunk in self.stream(self._build_prompt(HINT_PROMPT, problem)):
            yield chunk

    async def stream_approach(self, problem: Problem):
        async for chunk in self.stream(self._build_prompt(APPROACH_PROMPT, problem)):
            yield chunk

    async def stream_solution(self, problem: Problem):
        async for chunk in self.stream(self._build_prompt(SOLUTION_PROMPT, problem)):
            yield chunk

    async def stream_ask(self, problem: Problem, question: str, context: str = ""):
        ctx = f"이전 대화:\n{context}\n\n" if context else ""
        async for chunk in self.stream(self._build_prompt(ASK_PROMPT, problem, question=question, context=ctx)):
            yield chunk
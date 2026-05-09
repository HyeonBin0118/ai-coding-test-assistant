import os
from openai import AsyncOpenAI

from ..schemas.models import Problem
from .base import BaseLLMClient


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


HINT_PROMPT = """다음 코딩 문제를 풀 때 유용한 핵심 키워드와 함수만 알려주세요.

규칙:
- 2~4개 항목만
- 각 항목은 한 줄: `키워드/함수` — 한 줄 설명
- 코드는 짧은 예시 표현식 수준만 (예: n % 2 == 0)
- 알고리즘 이름, 내장 함수, 연산자 위주
- 설명 없이 목록만

문제: {title}
설명: {description}
제한사항: {constraints}"""


APPROACH_PROMPT = """다음 코딩 문제의 풀이 접근법을 설명하세요.

규칙:
- h1, h2, h3 헤더(#)를 절대 사용하지 마세요
- 번호 목록으로만 구성하세요
- 사용할 알고리즘과 자료구조를 **볼드**로 강조하세요
- 코드는 작성하지 마세요
- 시간복잡도를 마지막에 명시하세요
- 전체 4~6줄 이내로 간결하게

문제: {title}
설명: {description}
제한사항: {constraints}"""


SOLUTION_PROMPT = """다음 코딩 문제의 Python 정답 코드만 작성하세요.

- ```python 코드블록 없이 순수 파이썬 코드만 반환하세요
- 주석, 설명, 예제 테스트 없이 solution 함수만
- 들여쓰기는 반드시 4칸 스페이스

문제: {title}
설명: {description}
제한사항: {constraints}
예제: {examples}"""


ASK_PROMPT = """코딩 문제를 풀고 있는 사람의 질문에 간결하게 답하세요.

규칙:
- 핵심만 3~5줄로 짧게
- 헤더(#) 사용 금지
- 예시 코드는 꼭 필요할 때만, 있다면 ```python 블록으로
- 요약, 정리 섹션 없이 바로 본론만

문제: {title}
{context}질문: {question}"""


def build_prompt(template: str, problem: Problem, **kwargs) -> str:
    return template.format(
        title=problem.title,
        description=problem.description,
        constraints=problem.constraints,
        examples=problem.examples,
        **kwargs,
    )


class OpenAIClient(BaseLLMClient):

    async def _call(self, prompt: str) -> str:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    async def _stream(self, prompt: str):
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

    def _ask_context(self, context: str) -> str:
        return f"이전 대화:\n{context}\n\n" if context else ""

    async def get_hint(self, problem: Problem) -> str:
        return await self._call(build_prompt(HINT_PROMPT, problem))

    async def get_approach(self, problem: Problem) -> str:
        return await self._call(build_prompt(APPROACH_PROMPT, problem))

    async def get_solution(self, problem: Problem) -> str:
        return await self._call(build_prompt(SOLUTION_PROMPT, problem))

    async def ask(self, problem: Problem, question: str, context: str = "") -> str:
        prompt = build_prompt(ASK_PROMPT, problem, question=question, context=self._ask_context(context))
        return await self._call(prompt)

    async def stream_hint(self, problem: Problem):
        async for chunk in self._stream(build_prompt(HINT_PROMPT, problem)):
            yield chunk

    async def stream_approach(self, problem: Problem):
        async for chunk in self._stream(build_prompt(APPROACH_PROMPT, problem)):
            yield chunk

    async def stream_solution(self, problem: Problem):
        async for chunk in self._stream(build_prompt(SOLUTION_PROMPT, problem)):
            yield chunk

    async def stream_ask(self, problem: Problem, question: str, context: str = ""):
        prompt = build_prompt(ASK_PROMPT, problem, question=question, context=self._ask_context(context))
        async for chunk in self._stream(prompt):
            yield chunk
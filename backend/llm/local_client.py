from openai import AsyncOpenAI

from ..config import LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL
from ..schemas.models import Problem
from .base import BaseLLMClient
from .openai_client import HINT_PROMPT, APPROACH_PROMPT, SOLUTION_PROMPT, ASK_PROMPT, build_prompt


client = AsyncOpenAI(api_key="not-needed", base_url=LOCAL_LLM_BASE_URL)


class LocalClient(BaseLLMClient):
    """파인튜닝한 Qwen2.5-Coder-7B(v5)를 자체 구현한 OpenAI 호환 서버(serve_v5.py)로 호출하는 클라이언트.
    OpenAIClient와 동일한 프롬프트를 재사용하며, 엔드포인트만 로컬 서버로 바뀐다."""

    async def _call(self, prompt: str) -> str:
        response = await client.chat.completions.create(
            model=LOCAL_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    async def _stream(self, prompt: str):
        response = await client.chat.completions.create(
            model=LOCAL_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
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
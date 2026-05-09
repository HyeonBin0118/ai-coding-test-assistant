from abc import ABC, abstractmethod
from ..schemas.models import Problem


class BaseLLMClient(ABC):

    @abstractmethod
    async def get_hint(self, problem: Problem) -> str:
        """코드나 알고리즘 이름 없이 방향만 제시"""
        pass

    @abstractmethod
    async def get_approach(self, problem: Problem) -> str:
        """사용할 알고리즘/자료구조 설명, 코드 없이"""
        pass

    @abstractmethod
    async def get_solution(self, problem: Problem) -> str:
        """정답 코드 + 설명"""
        pass

    @abstractmethod
    async def ask(self, problem: Problem, question: str, context: str = "") -> str:
        """자유 질문"""
        pass
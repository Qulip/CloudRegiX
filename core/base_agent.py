from abc import ABC, abstractmethod
from typing import Any, Dict

from core import get_llm


class BaseAgent(ABC):
    """
    LangGraph 기반 Agent 추상 클래스

    Args:
        name (str): Agent 이름
    """

    def __init__(self, name: str):
        self.name = name
        self.llm = get_llm()

    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM 입력 Context 전처리 메서드

        Args:
            inputs (Dict[str, Any]): 입력 데이터

        Returns:
            Dict[str, Any]: 처리된 결과
        """
        return inputs

    @abstractmethod
    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        LLM 입력 Context 생성 메서드

        Args:
            inputs (Dict[str, Any]): 입력 데이터
        """
        pass

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent의 LLM 호출 메서드

        Args:
            inputs (Dict[str, Any]): 입력 데이터

        Returns:
            Dict[str, Any]: 처리된 결과
        """
        prompt = self._create_prompt(inputs)
        response = self.llm.invoke(prompt)
        return response

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM 답변 결과 후처리 메서드

        Args:
            outputs (Dict[str, Any]): 처리된 결과

        Returns:
            Dict[str, Any]: 처리된 결과
        """
        return outputs

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Node 연결을 위한 Callable 메서드

        Args:
            inputs (Dict[str, Any]): 입력 데이터

        Returns:
            Dict[str, Any]: 처리된 결과
        """
        inputs = self.preprocess(inputs)
        outputs = self.run(inputs)
        return self.postprocess(outputs)

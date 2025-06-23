from core import BaseAgent


class StreamAgent(BaseAgent):
    """
    LangGraph 기반 Streaming Agent 추상 클래스
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.streaming = True

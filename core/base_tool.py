from abc import ABC, abstractmethod


class BaseTool(ABC):
    @abstractmethod
    def run(self, inputs: dict) -> dict:
        pass

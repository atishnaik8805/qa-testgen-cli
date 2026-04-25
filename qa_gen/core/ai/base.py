from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        context: str,
        story_prompt: str,
        timeout: int = 60,
    ) -> str: ...

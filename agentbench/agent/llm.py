import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_call: Optional[dict] = field(default=None)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> LLMResponse:
        raise NotImplementedError


_PROVIDERS: dict[str, type[LLMProvider]] = {}


def get_provider(name: str, model: str) -> LLMProvider:
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise ValueError(f"Unknown provider: {name}")
    return provider_cls(model=model)

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


def _register_gemini() -> None:
    if "gemini" not in _PROVIDERS:
        from agentbench.agent.providers.gemini_provider import GeminiProvider

        _PROVIDERS["gemini"] = GeminiProvider


def get_provider(name: str, model: str) -> LLMProvider:
    if name == "gemini":
        _register_gemini()
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise ValueError(f"Unknown provider: {name}")
    return provider_cls(model=model)

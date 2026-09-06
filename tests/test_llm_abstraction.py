import pytest

from agentbench.agent.llm import LLMProvider, LLMResponse, get_provider


class FakeProvider(LLMProvider):
    def __init__(self, model: str = "fake"):
        self.model = model
        self.calls = []

    def generate(self, messages, tools, system):
        self.calls.append((messages, tools, system))
        return LLMResponse(
            content="hello",
            tool_call={"name": "bash", "arguments": '{"cmd": "ls"}'},
            input_tokens=10,
            output_tokens=5,
            model=self.model,
        )


def test_llm_response_defaults():
    resp = LLMResponse()
    assert resp.content is None
    assert resp.tool_call is None
    assert resp.input_tokens == 0
    assert resp.output_tokens == 0
    assert resp.model == ""


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


def test_llm_provider_interface_contract():
    provider = FakeProvider(model="fake-1")
    messages = [{"role": "user", "content": "hi"}]
    tools = [{"name": "bash"}]
    system = "be helpful"

    resp = provider.generate(messages, tools, system)

    assert provider.calls == [(messages, tools, system)]
    assert isinstance(resp, LLMResponse)
    assert resp.content == "hello"
    assert resp.tool_call == {"name": "bash", "arguments": '{"cmd": "ls"}'}
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.model == "fake-1"


def test_get_provider_returns_provider_subclass():
    provider = FakeProvider(model="m")
    assert isinstance(provider, LLMProvider)


def test_get_provider_unknown_raises_value_error():
    with pytest.raises(ValueError):
        get_provider("unknown", "x")

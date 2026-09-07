import pytest

from agentbench.agent.llm import LLMProvider, LLMResponse, get_provider


class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeUsageMetadata:
    def __init__(self, prompt=None, candidates=None):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates


class FakeResponse:
    def __init__(self, text=None, function_calls=None, metadata=None):
        self.text = text
        self.function_calls = function_calls
        self.usage_metadata = metadata


class FakeModels:
    def __init__(self, response):
        self._response = response
        self.last_call = None

    def generate_content(self, **kwargs):
        self.last_call = kwargs
        return self._response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


def _make_provider(monkeypatch, response):
    client = FakeClient(response)

    def make_client(api_key=None):
        return client

    monkeypatch.setattr(
        "agentbench.agent.providers.gemini_provider.genai.Client",
        make_client,
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    from agentbench.agent.providers.gemini_provider import GeminiProvider

    return GeminiProvider(model="gemini-2.0-flash"), client


def test_get_provider_gemini_returns_gemini_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(
        "agentbench.agent.providers.gemini_provider.genai.Client",
        lambda api_key=None: object(),
    )
    provider = get_provider("gemini", "gemini-2.0-flash")
    assert isinstance(provider, LLMProvider)
    from agentbench.agent.providers.gemini_provider import GeminiProvider

    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-2.0-flash"


def test_missing_api_key_raises_clear_value_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from agentbench.agent.providers.gemini_provider import GeminiProvider

    with pytest.raises(ValueError) as excinfo:
        GeminiProvider(model="gemini-2.0-flash")
    assert "GEMINI_API_KEY" in str(excinfo.value)


def test_text_response_translates_to_content(monkeypatch):
    response = FakeResponse(text="Hello there")
    provider, client = _make_provider(monkeypatch, response)

    result = provider.generate(
        [{"role": "user", "content": "hi"}],
        [],
        "system prompt",
    )

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello there"
    assert result.tool_call is None
    assert result.model == "gemini-2.0-flash"
    assert client.models.last_call["model"] == "gemini-2.0-flash"


def test_function_call_translates_to_tool_call(monkeypatch):
    response = FakeResponse(
        text=None,
        function_calls=[
            FakeFunctionCall(name="bash", args={"cmd": "ls", "flag": "-la"})
        ],
    )
    provider, client = _make_provider(monkeypatch, response)

    result = provider.generate(
        [{"role": "user", "content": "list files"}],
        [{"name": "bash", "description": "run a command"}],
        "system prompt",
    )

    assert result.content is None
    assert result.tool_call == {
        "name": "bash",
        "arguments": {"cmd": "ls", "flag": "-la"},
    }
    assert result.model == "gemini-2.0-flash"


def test_token_usage_translation(monkeypatch):
    response = FakeResponse(
        text="some text",
        metadata=FakeUsageMetadata(prompt=125, candidates=37),
    )
    provider, client = _make_provider(monkeypatch, response)

    result = provider.generate(
        [{"role": "user", "content": "hi"}],
        [],
        "system prompt",
    )

    assert result.input_tokens == 125
    assert result.output_tokens == 37
    assert result.model == "gemini-2.0-flash"


def test_missing_usage_gives_zero_tokens(monkeypatch):
    response = FakeResponse(text="no metadata here", metadata=None)
    provider, client = _make_provider(monkeypatch, response)

    result = provider.generate(
        [{"role": "user", "content": "hi"}],
        [],
        "system prompt",
    )

    assert result.input_tokens == 0
    assert result.output_tokens == 0


def test_model_name_is_preserved(monkeypatch):
    response = FakeResponse(text="hi")
    provider, client = _make_provider(monkeypatch, response)

    result = provider.generate(
        [{"role": "user", "content": "hi"}],
        [],
        "system prompt",
    )

    assert result.model == "gemini-2.0-flash"
    assert client.models.last_call["model"] == "gemini-2.0-flash"

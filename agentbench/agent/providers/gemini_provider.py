from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agentbench.agent.llm import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """LLMProvider backed by Google's Gemini API via the google-genai SDK."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        load_dotenv()
        self.model = model
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable must be set to use the "
                "Gemini provider"
            )
        self._api_key = api_key
        self._client = genai.Client(api_key=api_key)

    def generate(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> LLMResponse:
        contents = self._to_contents(messages)
        gemini_tools = self._to_tools(tools)

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return self._to_llm_response(response)

    def _to_contents(self, messages: list[dict]) -> list[types.Content]:
        contents: list[types.Content] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "assistant":
                gemini_role = "model"
            elif role == "system":
                gemini_role = "user"
            else:
                gemini_role = role
            if content is not None:
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_text(text=str(content))],
                    )
                )
        return contents

    def _to_tools(self, tools: list[dict]) -> list[types.Tool] | None:
        if not tools:
            return None
        declarations = []
        for tool in tools:
            parameters = tool.get("parameters") or {}
            declarations.append(
                types.FunctionDeclaration(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters_json_schema=parameters,
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _to_llm_response(self, response) -> LLMResponse:
        content = getattr(response, "text", None)

        tool_call = None
        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            first = function_calls[0]
            arguments = {}
            if first.args is not None:
                arguments = first.args
            tool_call = {
                "name": first.name,
                "arguments": arguments,
            }

        input_tokens = 0
        output_tokens = 0
        metadata = getattr(response, "usage_metadata", None)
        if metadata is None:
            metadata = getattr(response, "used_metadata", None)
        if metadata is not None:
            input_tokens = getattr(metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(metadata, "candidates_token_count", 0) or 0

        return LLMResponse(
            content=content,
            tool_call=tool_call,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
        )

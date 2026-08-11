"""Provider abstraction for the public NOVA demonstration.

Shows the same architecture pattern as the private project:
- Gemini online provider
- Ollama offline fallback
- Mock provider for public demos without keys

Never exposes private credentials or secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class Message:
    role: str
    text: str


@dataclass
class TurnResult:
    text: str
    raw: object = None
    error: str | None = None


def _gemini_client_available() -> bool:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False
    try:
        import google.genai  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def _ollama_available() -> bool:
    import httpx

    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=1)
        return response.status_code == 200
    except Exception:
        return False


class BaseProvider:
    def __init__(self, config: object) -> None:
        self.config = config

    def supports_tools(self) -> bool:  # pragma: no cover - interface
        return False

    def run_turn(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Iterable[object] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> TurnResult:
        raise NotImplementedError


class MockProvider(BaseProvider):
    def supports_tools(self) -> bool:
        return True

    def run_turn(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Iterable[object] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> TurnResult:
        last_user = ""
        for message in reversed(messages):
            if message.role == "user":
                last_user = message.text
                break
        last_user = (last_user or "").strip()
        available_tools = sorted({getattr(tool, "name", "?") for tool in tools or []})
        text = (
            "This is a public demonstration response from the mock provider.\n"
            f"User said: {last_user or '(no input)'}\n"
            f"Available tools in this demo: {', '.join(available_tools) or 'none'}\n"
            "Set GEMINI_API_KEY or start Ollama to use the real online/offline providers."
        )
        if on_chunk:
            on_chunk(text)
        return TurnResult(text=text, raw={"mode": "mock", "input": last_user})


class GeminiProvider(BaseProvider):
    def supports_tools(self) -> bool:
        return True

    def run_turn(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Iterable[object] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> TurnResult:
        if not _gemini_client_available():
            return TurnResult(
                text="Gemini is configured in this demo but the SDK or API key is unavailable.",
                error="missing_gemini",
            )
        from google import genai
        from google.genai import types

        client = genai.Client()
        model = getattr(self.config, "model_name", "gemini-2.5-flash")
        gemini_messages = []
        for message in messages:
            if message.role == "user":
                gemini_messages.append({"role": "user", "parts": [message.text]})
            else:
                gemini_messages.append({"role": "model", "parts": [message.text]})

        tool_schemas = []
        for tool in tools or []:
            schema = getattr(tool, "schema", {})
            if schema:
                tool_schemas.append(schema)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=getattr(self.config, "temperature", 0.7),
            max_output_tokens=getattr(self.config, "max_tokens", 512),
        )
        if tool_schemas:
            config.tools = tool_schemas

        response = client.models.generate_content_stream(
            model=model, contents=gemini_messages, config=config
        )
        collected = []
        for chunk in response:
            text = getattr(chunk, "text", None)
            if text:
                collected.append(text)
                if on_chunk:
                    on_chunk(text)
        return TurnResult(text="".join(collected), raw=response)


class OllamaProvider(BaseProvider):
    def supports_tools(self) -> bool:
        return False

    def run_turn(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Iterable[object] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> TurnResult:
        import httpx

        if not _ollama_available():
            return TurnResult(
                text="Ollama fallback requested, but no local server was detected.",
                error="ollama_unavailable",
            )
        chat_messages = [{"role": "system", "content": system_prompt}]
        for message in messages:
            role = "user" if message.role == "user" else "assistant"
            chat_messages.append({"role": role, "content": message.text})

        text_parts = []
        with httpx.stream(
            "POST",
            "http://localhost:11434/api/chat",
            json={"model": "llama3.1", "messages": chat_messages, "stream": True},
            timeout=120,
        ) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = httpx.Response(200, content=line).json()
                except Exception:
                    continue
                content = (((data or {}).get("message") or {}).get("content") or "")
                if content:
                    text_parts.append(content)
                    if on_chunk:
                        on_chunk(content)
                if data.get("done"):
                    break
        return TurnResult(text="".join(text_parts), raw={"mode": "ollama"})


def resolve_provider(config: object) -> BaseProvider:
    provider_name = getattr(config, "provider", "mock").lower()
    if provider_name == "gemini" and _gemini_client_available():
        return GeminiProvider(config)
    if provider_name == "ollama" and _ollama_available():
        return OllamaProvider(config)
    if provider_name == "gemini":
        return GeminiProvider(config)
    if provider_name == "ollama":
        return OllamaProvider(config)
    return MockProvider(config)

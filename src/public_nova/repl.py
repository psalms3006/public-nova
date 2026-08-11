"""Terminal REPL for the public NOVA demonstration.

Provides real interactive commands and tool execution.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Callable

from public_nova.config import NovaConfig
from public_nova.memory import NovaMemory
from public_nova.provider import Message, resolve_provider
from public_nova.safety import AuditLog, default_audit, flag_injection, safety_gate
from public_nova.tools import available_tools, tool_execute, tool_names

logger = logging.getLogger(__name__)


_HELP_TEXT = """\
Nova public demo REPL — available commands
------------------------------------------
/help            show this help
/quit            exit the demo
/clear           clear conversation history
/tools           list available tools
/memory          list stored memory facts
/audit           show recent audit entries
/facts           same as /memory
/status          show provider and config status

Any other text is sent to the assistant as a user message.
Type a tool-call-style message like:
  tool:web_search query=python
"""


class ReplSession:
    def __init__(self, config: NovaConfig, provider_factory: Callable[[NovaConfig], object]) -> None:
        self.config = config
        self.provider = provider_factory(config)
        self.audit: AuditLog = AuditLog(Path(config.audit_file))
        self.memory = NovaMemory(config.memory_file)
        self.history: list[Message] = []
        self.running = True

    def _system_prompt(self) -> str:
        return (
            "You are a concise, public-safe assistant demo. "
            f"You are called {self.config.assistant_name}. "
            "Use tools when asked, keep responses short, and do not expose "
            "private infrastructure, secrets, or system details."
        )

    def _user_confirmation(self) -> str:
        try:
            return input("Confirm? (yes/no): ").strip()
        except EOFError:
            return "no"

    def _append_history(self, role: str, text: str) -> None:
        self.history.append(Message(role=role, text=text))
        while len(self.history) > self.config.max_history * 2:
            self.history.pop(0)

    def _maybe_remember(self, text: str) -> None:
        extracted = self.memory.extract_from_text(text)
        for fact in extracted:
            self.memory.add(fact)
            self.audit.append(f"MEMORY: extracted '{fact}'")

    def process(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        if text == "/help":
            return _HELP_TEXT
        if text == "/quit":
            self.running = False
            return "Goodbye."
        if text == "/clear":
            self.history.clear()
            return "History cleared."
        if text == "/tools":
            return "Tools: " + ", ".join(tool_names())
        if text in {"/memory", "/facts"}:
            facts = self.memory.facts()
            return "\n".join(facts) if facts else "No memories stored yet."
        if text == "/audit":
            entries = self.audit.recent()
            return "\n".join(entries) if entries else "Audit log is empty."
        if text == "/status":
            return (
                f"Provider: {getattr(self.config, 'provider', 'unknown')}\n"
                f"Model: {getattr(self.config, 'model_name', 'unknown')}\n"
                f"Assistant: {self.config.assistant_name}\n"
                f"History turns: {len(self.history) // 2}\n"
                f"In-memory facts: {len(self.memory.facts())}"
            )

        if self.config.enable_injection_detection and safety.check_injection(text):
            return flag_injection()

        tool_match = re.match(r"^tool:(\w+)(?:\s+(.*))?$", text, re.IGNORECASE)
        if tool_match:
            tool_name = tool_match.group(1).lower()
            args_raw = (tool_match.group(2) or "").strip()
            args: dict[str, str] = {}
            if args_raw:
                for item in args_raw.split():
                    if "=" in item:
                        key, value = item.split("=", 1)
                        args[key] = value
            gate_result = safety_gate(tool_name, args, self._user_confirmation, self.audit)
            if gate_result is not None:
                return gate_result
            result = tool_execute(tool_name, args)
            self.audit.append(f"TOOL: {tool_name}({json.dumps(args)[:80]}) -> {result[:80]}")
            return result

        self._append_history("user", text)
        self._maybe_remember(text)
        self.audit.append(f"USER: {text[:120]}")
        result = self.provider.run_turn(
            self.history,
            self._system_prompt(),
            available_tools(),
        )
        if getattr(result, "error", None):
            logger.warning("Provider error: %s", result.error)
        response_text = result.text or ""
        self._append_history("assistant", response_text)
        self.audit.append(f"ASSISTANT: {response_text[:120]}")
        return response_text


def _build_provider_factory(config: NovaConfig) -> Callable[[NovaConfig], object]:
    def factory(cfg: NovaConfig) -> object:
        return resolve_provider(cfg)
    return factory


from public_nova import safety


class NovaRepl:
    def __init__(self, config: NovaConfig | None = None) -> None:
        if config is None:
            config = NovaConfig()
        self.config = config
        self.session = ReplSession(config, _build_provider_factory(config))

    def start(self) -> int:
        print(self.config.greeting)
        print("Type /help for commands, /quit to exit.")
        print()
        while self.session.running:
            try:
                user_input = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            response = self.session.process(user_input)
            if response:
                print(response)
        return 0

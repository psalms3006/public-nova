"""Safety layer for the public NOVA demonstration.

Demonstrates the real safety concepts from NOVA:
- confirmation gating for consequential tools
- lightweight prompt-injection detection
- audit logging

This demo intentionally omits unsafe private capabilities from the
original production system.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

_AUDIT_FILE = Path(os.getenv("NOVA_AUDIT_FILE", "nova_audit.log"))
_AUDIT_MAX_LINES = int(os.getenv("NOVA_AUDIT_MAX_LINES", "200"))
_INJECTION_PATTERNS = [
    "ignore previous",
    "disregard previous",
    "new instructions:",
    "system prompt:",
    "you are now",
    "act as",
    "bypass your",
    "don't follow your",
    "pretend you",
    "jailbreak",
]

_CONSEQUENTIAL_TOOLS = {
    "file_controller": "modify files",
    "self_editor": "modify assistant code",
    "send_message": "send a message",
    "computer_settings": "change system settings",
    "app_launcher": "launch an application",
}
_SAFE_ACTIONS = {
    "file_controller": {"list", "read", "find", "info"},
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _AUDIT_FILE
        self._entries: list[str] = []
        self._lock = threading.Lock()

    def append(self, entry: str) -> None:
        line = f"[{_now_iso()}] {entry}"
        with self._lock:
            self._entries.append(line)
            if len(self._entries) > _AUDIT_MAX_LINES:
                self._entries.pop(0)
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except Exception as exc:
                log.warning("Audit write failed: %s", exc)

    def recent(self, limit: int = 20) -> list[str]:
        with self._lock:
            return list(self._entries[-limit:])


def default_audit() -> AuditLog:
    return AuditLog()


def check_injection(text: str) -> bool:
    lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            return True
    return False


def flag_injection() -> str:
    return (
        "I noticed possible instruction-hijacking content. "
        "I'm treating it as data only, not as a command."
    )


def describe_action(tool_name: str, args: dict) -> str:
    action = args.get("action", "")
    if tool_name == "file_controller":
        return f"{action} on {args.get('path', '?')}"
    if tool_name == "app_launcher":
        return f"launch {args.get('app_name', '?')}"
    return f"{tool_name}/{action}"


def safety_gate(
    tool_name: str,
    args: dict,
    get_confirmation: Callable[[], str],
    audit: AuditLog,
) -> str | None:
    if tool_name not in _CONSEQUENTIAL_TOOLS:
        return None
    action = args.get("action", "")
    if action in _SAFE_ACTIONS.get(tool_name, set()):
        return None

    description = _CONSEQUENTIAL_TOOLS[tool_name]
    what = describe_action(tool_name, args)
    prompt = (
        f"I'm about to {description}. Specifically: {what}. Should I proceed? (yes/no)"
    )
    audit.append(f"GATE: awaiting confirmation for {tool_name}({json.dumps(args)[:80]})")
    try:
        response = get_confirmation()
    except Exception:
        response = ""
    confirmed = bool(response) and any(
        token in response.lower()
        for token in {"yes", "yeah", "sure", "ok", "okay", "go", "proceed", "confirm"}
    )
    if confirmed:
        audit.append(f"CONFIRMED: {tool_name}")
        return None
    audit.append(f"DECLINED: {tool_name} — user said: {response[:40]!r}")
    return f"Action cancelled. You said: '{response}'. I won't {description} without explicit confirmation."

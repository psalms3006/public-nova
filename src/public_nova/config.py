"""Configuration loader for the public NOVA demonstration.

Reads settings from environment variables with safe defaults. No
production-only behavior is included.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class NovaConfig:
    assistant_name: str = os.getenv("NOVA_NAME", "Nova")
    provider: str = os.getenv("NOVA_PROVIDER", "mock").lower()
    model_name: str = os.getenv("NOVA_MODEL", "gemini-2.5-flash")
    temperature: float = float(os.getenv("NOVA_TEMPERATURE", "0.7"))
    max_tokens: int = _env_int("NOVA_MAX_TOKENS", 512)
    max_history: int = _env_int("NOVA_MAX_HISTORY", 8)
    memory_file: str = os.getenv("NOVA_MEMORY_FILE", "nova_memory.json")
    audit_file: str = os.getenv("NOVA_AUDIT_FILE", "nova_audit.log")
    enable_audit: bool = _env_bool("NOVA_ENABLE_AUDIT", True)
    enable_injection_detection: bool = _env_bool("NOVA_ENABLE_INJECTION_DETECTION", True)
    greeting: str = (
        "Hi — I'm Nova. I can answer questions, search the web, manage files, "
        "and launch apps. Ask me anything."
    )

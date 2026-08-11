"""Memory layer for the public NOVA demonstration.

Demonstrates durable in-session memory and simple memory extraction
without exposing private memory implementations or filesystem details.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


_MEMORY_PATTERNS = [
    re.compile(r"(?:my name is|call me)\s+([A-Za-z][A-Za-z0-9_-]+(?:\s+[A-Za-z][A-Za-z0-9_-]+){0,2})", re.IGNORECASE),
    re.compile(r"(?:i live in|i'm from|i am from)\s+([A-Za-z][A-Za-z0-9_-]+(?:\s+[A-Za-z][A-Za-z0-9_-]+){0,2})", re.IGNORECASE),
    re.compile(r"(?:my favorite|i prefer)\s+([A-Za-z][A-Za-z0-9_-]+(?:\s+[A-Za-z][A-Za-z0-9_-]+){0,2})", re.IGNORECASE),
    re.compile(r"(?:my favorite|i prefer)\s+[A-Za-z][A-Za-z0-9_-]+(?:\s+[A-Za-z][A-Za-z0-9_-]+){0,2}\s+(?:is|are)\s+(.+)", re.IGNORECASE),
]


def _clean(text: str) -> str:
    return " ".join(text.split())


@dataclass
class MemoryEntry:
    text: str
    source: str = "user"
    tags: tuple[str, ...] = ()
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class NovaMemory:
    def __init__(self, memory_file: str) -> None:
        self.memory_file = Path(memory_file)
        self.entries: list[MemoryEntry] = []
        self._load()

    def _load(self) -> None:
        if not self.memory_file.exists():
            self.entries = []
            return
        try:
            data = json.loads(self.memory_file.read_text(encoding="utf-8"))
            self.entries = [
                MemoryEntry(
                    text=item["text"],
                    source=item.get("source", "user"),
                    tags=tuple(item.get("tags", [])),
                    timestamp=item.get("timestamp", ""),
                )
                for item in data
            ]
        except Exception as exc:
            log.warning("Memory load failed: %s", exc)
            self.entries = []

    def _save(self) -> None:
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            self.memory_file.write_text(
                json.dumps(
                    [
                        {
                            "text": entry.text,
                            "source": entry.source,
                            "tags": list(entry.tags),
                            "timestamp": entry.timestamp,
                        }
                        for entry in self.entries
                    ],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            log.warning("Memory save failed: %s", exc)

    def add(self, text: str, source: str = "user", tags: Iterable[str] | None = None) -> None:
        entry = MemoryEntry(
            text=text,
            source=source,
            tags=tuple(sorted({tag.lower() for tag in (tags or []) if tag})),
        )
        self.entries.append(entry)
        self._save()

    def search(self, query: str, max_results: int = 5) -> list[MemoryEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self.entries:
            score = 0
            if query_lower in entry.text.lower():
                score += 2
            if query_lower in " ".join(entry.tags):
                score += 1
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]

    def extract_from_text(self, text: str) -> list[str]:
        extracted = []
        for pattern in _MEMORY_PATTERNS:
            match = pattern.search(text)
            if match:
                candidate = _clean(match.group(1))
                if 2 <= len(candidate) <= 120:
                    extracted.append(candidate)
        return extracted

    def facts(self, max_results: int = 20) -> list[str]:
        return [entry.text for entry in self.entries[-max_results:]]

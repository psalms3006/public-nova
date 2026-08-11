"""Tool registry and safe demo tools for the public NOVA demonstration.

Demonstrates the concept of a local tool registry while intentionally
leaving out unsafe private production tools.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    handler: Callable[[dict], str]


_TOOL_REGISTRY: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    _TOOL_REGISTRY[tool.name] = tool


def available_tools() -> list[Tool]:
    return list(_TOOL_REGISTRY.values())


def tool_names() -> list[str]:
    return sorted(_TOOL_REGISTRY)


def get_tool(name: str) -> Tool | None:
    return _TOOL_REGISTRY.get(name)


def reset_tools() -> None:
    _TOOL_REGISTRY.clear()


def tool_execute(tool_name: str, args: dict) -> str:
    tool = get_tool(tool_name)
    if not tool:
        return f"Unknown tool: {tool_name}"
    try:
        return tool.handler(args)
    except Exception as exc:
        log.exception("Tool execution failed: %s", tool_name)
        return f"Tool failed: {tool_name} — {exc}"


def _web_search(args: dict) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        return "Please provide a search query."
    return (
        f"[Demo web search result for '{query}']\n"
        "This is a safe public demonstration. In the full private NOVA system, "
        "real search backends are available."
    )


def _file_list(args: dict) -> str:
    target = (args.get("path") or "").strip() or "."
    path = Path(target)
    if not path.exists():
        return f"Path not found: {path}"
    if not path.is_dir():
        return f"Not a directory: {path}"
    items = sorted(path.iterdir(), key=lambda item: item.name.lower())
    lines = [f"{'[DIR] ' if item.is_dir() else '[FILE]'} {item.name}" for item in items[:50]]
    return "\n".join(lines) if lines else f"Empty directory: {path}"


def _file_read(args: dict) -> str:
    target = (args.get("path") or "").strip()
    if not target:
        return "Please provide a file path."
    path = Path(target)
    if not path.exists() or not path.is_file():
        return f"File not found: {path}"
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:2000]
    except Exception as exc:
        return f"Read failed: {exc}"


def _app_launch(args: dict) -> str:
    app_name = (args.get("app_name") or "").strip()
    if not app_name:
        return "Please provide an app_name."
    safe_apps = {
        "notepad": "notepad",
        "calculator": "calc",
        "file explorer": "explorer",
        "explorer": "explorer",
    }
    system = platform.system()
    if system == "Windows":
        mapped = {
            "notepad": "notepad",
            "calculator": "calc",
            "explorer": "explorer",
            "file explorer": "explorer",
        }
    elif system == "Darwin":
        mapped = {
            "notepad": "open -a TextEdit",
            "calculator": "open -a Calculator",
            "file explorer": "open .",
            "explorer": "open .",
        }
    else:
        mapped = {name: name for name in safe_apps}

    command = mapped.get(app_name.lower())
    if not command:
        return f"App launch is restricted in the public demo. Try: {', '.join(sorted(mapped))}"
    try:
        subprocess.Popen(command, shell=True)
        return f"Launched: {app_name}"
    except Exception as exc:
        return f"Launch failed: {exc}"


def _memory_search(args: dict) -> str:
    from public_nova.memory import NovaMemory

    query = (args.get("query") or "").strip()
    if not query:
        return "Please provide a query."
    memory = NovaMemory(os.getenv("NOVA_MEMORY_FILE", "nova_memory.json"))
    results = memory.search(query)
    if not results:
        return "No matching memory entries found."
    return "\n".join(f"- {entry.text}" for entry in results)


def _memory_add(args: dict) -> str:
    from public_nova.memory import NovaMemory

    text = (args.get("text") or "").strip()
    if not text:
        return "Please provide text to remember."
    memory = NovaMemory(os.getenv("NOVA_MEMORY_FILE", "nova_memory.json"))
    memory.add(text)
    return f"Remembered: {text}"


def _memory_facts(args: dict) -> str:
    from public_nova.memory import NovaMemory

    memory = NovaMemory(os.getenv("NOVA_MEMORY_FILE", "nova_memory.json"))
    facts = memory.facts()
    if not facts:
        return "No memories stored yet."
    return "\n".join(f"- {fact}" for fact in facts)


def _system_status(args: dict) -> str:
    return (
        f"System: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
        f"Loaded tools: {', '.join(tool_names()) or 'none'}"
    )


def load_default_tools() -> None:
    reset_tools()
    register_tool(
        Tool(
            name="web_search",
            description="Search the web for a topic.",
            schema={
                "name": "web_search",
                "description": "Search the web for a topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query."}
                    },
                    "required": ["query"],
                },
            },
            handler=_web_search,
        )
    )
    register_tool(
        Tool(
            name="file_list",
            description="List files and directories.",
            schema={
                "name": "file_list",
                "description": "List files and directories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path."}
                    },
                    "required": [],
                },
            },
            handler=_file_list,
        )
    )
    register_tool(
        Tool(
            name="file_read",
            description="Read a text file.",
            schema={
                "name": "file_read",
                "description": "Read a text file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path."}
                    },
                    "required": ["path"],
                },
            },
            handler=_file_read,
        )
    )
    register_tool(
        Tool(
            name="app_launcher",
            description="Launch a local application in a safe demo allowlist.",
            schema={
                "name": "app_launcher",
                "description": "Launch a local application in a safe demo allowlist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Application name."}
                    },
                    "required": ["app_name"],
                },
            },
            handler=_app_launch,
        )
    )
    register_tool(
        Tool(
            name="memory_search",
            description="Search remembered facts.",
            schema={
                "name": "memory_search",
                "description": "Search remembered facts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Memory query."}
                    },
                    "required": ["query"],
                },
            },
            handler=_memory_search,
        )
    )
    register_tool(
        Tool(
            name="memory_add",
            description="Store a new durable memory.",
            schema={
                "name": "memory_add",
                "description": "Store a new durable memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to remember."}
                    },
                    "required": ["text"],
                },
            },
            handler=_memory_add,
        )
    )
    register_tool(
        Tool(
            name="memory_facts",
            description="List stored memory facts.",
            schema={
                "name": "memory_facts",
                "description": "List stored memory facts.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            handler=_memory_facts,
        )
    )
    register_tool(
        Tool(
            name="system_status",
            description="Show safe public system status.",
            schema={
                "name": "system_status",
                "description": "Show safe public system status.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            handler=_system_status,
        )
    )

"""Tool registry.

Each tool module exposes two things:
  * ``SCHEMAS``  - a list of Ollama/OpenAI-style function schemas, and
  * ``HANDLERS`` - a ``{name: fn}`` map where ``fn(arguments: dict, ctx) -> str``.

This package aggregates them into :data:`TOOLS_SCHEMA` (sent to the model) and a
single :func:`dispatch` entry point used by the agent loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import clock, web, system, reminders

_MODULES = [clock, web, system, reminders]

TOOLS_SCHEMA: list[dict] = [schema for m in _MODULES for schema in m.SCHEMAS]
_HANDLERS: dict[str, Callable[[dict, "ToolContext"], str]] = {
    name: fn for m in _MODULES for name, fn in m.HANDLERS.items()
}


@dataclass
class ToolContext:
    """Everything a tool might need, passed to every handler."""

    config: Any
    speaker: Any
    scheduler: Any
    confirm: Callable[[str], bool]
    notify: Callable[[str], None]


def tool_names() -> list[str]:
    return sorted(_HANDLERS)


def dispatch(name: str, arguments: dict, ctx: ToolContext) -> str:
    """Run a tool by name. Never raises — errors come back as text for the model."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'."
    try:
        return handler(arguments or {}, ctx)
    except Exception as exc:  # tools must not crash the agent loop
        return f"Error while running {name}: {exc}"

"""Date and time tool."""
from __future__ import annotations

from datetime import datetime

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


def _get_current_time(args: dict, ctx) -> str:
    return datetime.now().strftime("It is %A, %B %d %Y, %I:%M %p.")


HANDLERS = {"get_current_time": _get_current_time}

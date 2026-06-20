"""Clipboard read/write tools (Windows, via PowerShell — no extra dependency)."""
from __future__ import annotations

import subprocess

_TIMEOUT = 10

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Read the current text contents of the Windows clipboard.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_clipboard",
            "description": "Copy the given text onto the Windows clipboard.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Text to copy."}},
                "required": ["text"],
            },
        },
    },
]


def _read_clipboard(args: dict, ctx) -> str:
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        return f"Couldn't read the clipboard: {exc}"
    text = (proc.stdout or "").strip()
    return f"The clipboard contains: {text}" if text else "The clipboard is empty."


def _write_clipboard(args: dict, ctx) -> str:
    text = args.get("text") or ""
    if not text:
        return "There was nothing to copy."
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            input=text,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        return f"Couldn't write to the clipboard: {exc}"
    return "Copied to the clipboard."


HANDLERS = {"read_clipboard": _read_clipboard, "write_clipboard": _write_clipboard}

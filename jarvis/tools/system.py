"""PC-control tools: launch applications, run shell commands, report system info.

``run_command`` runs an arbitrary shell command, so it is gated behind
``ctx.confirm`` whenever ``config.confirm_commands`` is true — the agent supplies
a confirmation callback that asks the user before anything is executed.

``open_application`` only *launches* a named app/file/URL via the Windows shell
verb (``os.startfile``); it never runs a shell command line, and it rejects names
containing shell metacharacters, so it cannot be used to smuggle commands past the
``run_command`` confirmation gate.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess

_COMMAND_TIMEOUT = 30  # seconds
# Characters that could let a crafted name break out into command execution.
_UNSAFE_NAME_CHARS = set('&|<>^"%`\n\r')

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": (
                "Open an application or file on the Windows PC by name, e.g. "
                "'notepad', 'calc', 'chrome', 'explorer', or a file path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "App name, file, or URL to open."}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command on the Windows PC and return its output. Use "
                "for system actions the user explicitly asks for. The user is asked "
                "to confirm before the command runs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to run."}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Report basic system information (OS, CPU, Python, disk space).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _open_application(args: dict, ctx) -> str:
    name = (args.get("name") or "").strip().strip('"')
    if not name:
        return "No application name was provided."
    if any(ch in name for ch in _UNSAFE_NAME_CHARS):
        return f"Refusing to open '{name}': it contains unsafe characters."
    try:
        # ShellExecute: resolves App Paths (notepad, calc, chrome, explorer), and
        # opens files/URLs — without ever building a shell command line.
        os.startfile(name)  # type: ignore[attr-defined]  # Windows-only
        return f"Opening {name}."
    except FileNotFoundError:
        return f"I couldn't find anything called '{name}' to open."
    except OSError as exc:
        return f"Couldn't open {name}: {exc}"


def _run_command(args: dict, ctx) -> str:
    command = (args.get("command") or "").strip()
    if not command:
        return "No command was provided."
    if getattr(ctx.config, "confirm_commands", True):
        if not ctx.confirm(f"Run this command: {command}"):
            return "Command cancelled by the user."
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {_COMMAND_TIMEOUT} seconds."
    except Exception as exc:
        return f"Failed to run command: {exc}"

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    parts = [f"Exit code {proc.returncode}."]
    if out:
        parts.append(out[:1500])
    if err:
        parts.append("[stderr] " + err[:500])
    if not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)


def _system_info(args: dict, ctx) -> str:
    try:
        total, _used, free = shutil.disk_usage("C:\\")
        gb = lambda b: round(b / (1024 ** 3), 1)
        disk = f"C: drive {gb(free)} GB free of {gb(total)} GB"
    except Exception:
        disk = "disk info unavailable"
    return (
        f"Operating system: {platform.system()} {platform.release()}. "
        f"Processor: {platform.processor() or platform.machine()}. "
        f"Python {platform.python_version()}. {disk}."
    )


HANDLERS = {
    "open_application": _open_application,
    "run_command": _run_command,
    "system_info": _system_info,
}

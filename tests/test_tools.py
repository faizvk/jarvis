"""Tests for the tool registry and dispatch."""
from types import SimpleNamespace

from jarvis.tools import TOOLS_SCHEMA, dispatch, tool_names

EXPECTED = [
    "web_search", "open_url", "open_application", "run_command", "system_info",
    "set_timer", "set_reminder", "list_reminders", "cancel_reminder", "get_current_time",
]


def test_schema_shape():
    assert TOOLS_SCHEMA
    for schema in TOOLS_SCHEMA:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]


def test_expected_tools_present():
    names = set(tool_names())
    for name in EXPECTED:
        assert name in names


def test_dispatch_unknown_tool():
    assert "unknown tool" in dispatch("nope", {}, SimpleNamespace()).lower()


def test_dispatch_catches_handler_errors():
    # set_timer touches ctx.scheduler; a ctx without one must not crash the loop.
    out = dispatch("set_timer", {"duration_seconds": 10}, SimpleNamespace())
    assert out.lower().startswith("error")


def test_run_command_is_gated_by_confirmation():
    seen = {}
    ctx = SimpleNamespace(
        config=SimpleNamespace(confirm_commands=True),
        confirm=lambda prompt: seen.setdefault("prompt", prompt) and False,
    )
    out = dispatch("run_command", {"command": "echo hi"}, ctx)
    assert "cancelled" in out.lower()
    assert "echo hi" in seen["prompt"]


def test_system_info_reports_python():
    assert "Python" in dispatch("system_info", {}, SimpleNamespace())

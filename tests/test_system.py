"""Tests for the PC-control tools, focused on the safety behaviour."""
from types import SimpleNamespace

from jarvis.tools import dispatch
from jarvis.tools.system import _is_destructive


def _ctx(confirm_commands=True, confirm_returns=False, recorder=None):
    def confirm(prompt):
        if recorder is not None:
            recorder.append(prompt)
        return confirm_returns

    return SimpleNamespace(
        config=SimpleNamespace(confirm_commands=confirm_commands), confirm=confirm
    )


def test_destructive_detection():
    assert _is_destructive("del C:\\important.txt")
    assert _is_destructive("Remove-Item foo -Recurse")
    assert _is_destructive("shutdown /s")
    assert not _is_destructive("echo hello")
    assert not _is_destructive("dir")


def test_destructive_command_always_confirms_even_when_disabled():
    prompts = []
    # confirmation globally OFF, but a destructive command must still ask.
    ctx = _ctx(confirm_commands=False, confirm_returns=False, recorder=prompts)
    out = dispatch("run_command", {"command": "del important.txt"}, ctx)
    assert "cancelled" in out.lower()
    assert prompts and "del important.txt" in prompts[0]


def test_safe_command_runs_without_confirm_when_disabled():
    prompts = []
    ctx = _ctx(confirm_commands=False, confirm_returns=False, recorder=prompts)
    out = dispatch("run_command", {"command": "echo hello"}, ctx)
    assert "hello" in out
    assert prompts == []  # confirm was never called


def test_open_application_rejects_metacharacters():
    out = dispatch("open_application", {"name": "foo | calc"}, SimpleNamespace())
    assert "unsafe" in out.lower()


def test_system_info_reports_python():
    assert "Python" in dispatch("system_info", {}, SimpleNamespace())

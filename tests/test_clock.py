"""Tests for the clock tool."""
from types import SimpleNamespace

from jarvis.tools import clock


def test_get_current_time_speaks_a_date():
    out = clock.HANDLERS["get_current_time"]({}, SimpleNamespace())
    assert "It is" in out
    assert any(ch.isdigit() for ch in out)

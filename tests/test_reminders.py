"""Tests for the reminders/timers scheduler and tools."""
import time
from types import SimpleNamespace

from jarvis.tools.reminders import HANDLERS, Scheduler


def test_add_list_cancel(tmp_path):
    s = Scheduler(notify=lambda m: None, state_path=str(tmp_path / "r.json"))
    rid = s.add("hi", 100, kind="reminder", label="hi")
    items = s.list_items()
    assert len(items) == 1 and items[0]["id"] == rid
    assert s.cancel(rid) is True
    assert s.cancel(rid) is False
    assert s.list_items() == []


def test_persistence_across_instances(tmp_path):
    path = str(tmp_path / "r.json")
    rid = Scheduler(lambda m: None, path).add("buy milk", 100)
    reloaded = Scheduler(lambda m: None, path)
    assert any(i["id"] == rid for i in reloaded.list_items())


def test_due_item_fires(tmp_path):
    fired = []
    s = Scheduler(notify=fired.append, state_path=str(tmp_path / "r.json"))
    s.add("ping", 0.05)
    s.start()
    try:
        deadline = time.time() + 4
        while not fired and time.time() < deadline:
            time.sleep(0.05)
    finally:
        s.stop()
    assert fired == ["ping"]


def test_set_timer_tool(tmp_path):
    s = Scheduler(lambda m: None, str(tmp_path / "r.json"))
    ctx = SimpleNamespace(scheduler=s)
    out = HANDLERS["set_timer"]({"duration_seconds": 120, "label": "tea"}, ctx)
    assert "Timer set" in out
    assert len(s.list_items()) == 1


def test_set_reminder_validates_input(tmp_path):
    s = Scheduler(lambda m: None, str(tmp_path / "r.json"))
    ctx = SimpleNamespace(scheduler=s)
    assert "What should I remind" in HANDLERS["set_reminder"]({"delay_seconds": 10}, ctx)
    assert "When should I" in HANDLERS["set_reminder"]({"text": "x", "delay_seconds": 0}, ctx)

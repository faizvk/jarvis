"""Reminders and timers, backed by a small persistent background scheduler.

The :class:`Scheduler` runs a daemon thread that fires due items by calling a
``notify`` callback (the agent wires this to speech + console output). Items are
persisted to JSON so pending reminders survive a restart.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path


class Scheduler:
    def __init__(self, notify, state_path: str):
        self._notify = notify
        self._state_path = Path(state_path)
        self._items: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._load()

    # --- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="jarvis-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        # The whole body is guarded: a single malformed item must never be able
        # to kill the daemon thread and silently stop every future reminder.
        while not self._stop.wait(1.0):
            try:
                now = time.time()
                due = []
                with self._lock:
                    for item in list(self._items.values()):
                        if item.get("fire_at", float("inf")) <= now:
                            due.append(item)
                            del self._items[item["id"]]
                    if due:
                        self._save()
                for item in due:
                    try:
                        self._notify(item.get("message", ""))
                    except Exception:
                        pass
            except Exception:
                pass

    # --- operations ----------------------------------------------------------
    def add(self, message: str, delay_seconds: float, kind: str = "reminder", label: str = "") -> str:
        delay_seconds = max(0.0, float(delay_seconds))
        item_id = uuid.uuid4().hex[:8]
        with self._lock:
            self._items[item_id] = {
                "id": item_id,
                "kind": kind,
                "label": label,
                "message": message,
                "fire_at": time.time() + delay_seconds,
            }
            self._save()
        return item_id

    def list_items(self) -> list[dict]:
        with self._lock:
            return sorted(self._items.values(), key=lambda x: x["fire_at"])

    def cancel(self, item_id: str) -> bool:
        with self._lock:
            existed = item_id in self._items
            self._items.pop(item_id, None)
            if existed:
                self._save()
        return existed

    # --- persistence ---------------------------------------------------------
    def _load(self) -> None:
        if not self._state_path.is_file():
            return
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            # Only keep well-formed items so a hand-edited or older-schema file
            # can't crash the scheduler thread later.
            self._items = {
                item["id"]: item
                for item in data
                if isinstance(item, dict) and {"id", "fire_at", "message"} <= item.keys()
            }
        except Exception:
            self._items = {}

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then atomically replace, so a crash mid-write can't
        # truncate reminders.json (which would later kill the scheduler thread).
        tmp = self._state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(list(self._items.values())), encoding="utf-8")
        os.replace(tmp, self._state_path)


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Start a countdown timer that announces when it finishes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {"type": "integer", "description": "Length in seconds."},
                    "label": {"type": "string", "description": "Optional name for the timer."},
                },
                "required": ["duration_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder that is spoken aloud after a delay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to remind the user about."},
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds."},
                },
                "required": ["text", "delay_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List all active reminders and timers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "Cancel a reminder or timer by its id.",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string", "description": "The id to cancel."}},
                "required": ["id"],
            },
        },
    },
]


def _humanise(seconds: int) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minute(s)"
    return f"{seconds // 3600} hour(s) {(seconds % 3600) // 60} minute(s)"


def _set_timer(args: dict, ctx) -> str:
    seconds = int(args.get("duration_seconds") or 0)
    label = (args.get("label") or "").strip()
    if seconds <= 0:
        return "Please give a positive duration in seconds."
    message = f"Your timer is up{(': ' + label) if label else ''}."
    item_id = ctx.scheduler.add(message, seconds, kind="timer", label=label)
    return f"Timer set for {_humanise(seconds)} (id {item_id})."


def _set_reminder(args: dict, ctx) -> str:
    text = (args.get("text") or "").strip()
    seconds = int(args.get("delay_seconds") or 0)
    if not text:
        return "What should I remind you about?"
    if seconds <= 0:
        return "When should I remind you? Please give a delay in seconds."
    item_id = ctx.scheduler.add(f"Reminder: {text}", seconds, kind="reminder", label=text)
    return f"Okay, I'll remind you to {text} in {_humanise(seconds)} (id {item_id})."


def _list_reminders(args: dict, ctx) -> str:
    items = ctx.scheduler.list_items()
    if not items:
        return "You have no active reminders or timers."
    now = time.time()
    parts = []
    for item in items:
        remaining = max(0, int(item["fire_at"] - now))
        name = item["label"] or item["kind"]
        parts.append(f"{item['kind']} '{name}' in {_humanise(remaining)} (id {item['id']})")
    return "Active: " + "; ".join(parts) + "."


def _cancel_reminder(args: dict, ctx) -> str:
    item_id = (args.get("id") or "").strip()
    if not item_id:
        return "Which id should I cancel?"
    if ctx.scheduler.cancel(item_id):
        return f"Cancelled {item_id}."
    return f"I couldn't find anything with id {item_id}."


HANDLERS = {
    "set_timer": _set_timer,
    "set_reminder": _set_reminder,
    "list_reminders": _list_reminders,
    "cancel_reminder": _cancel_reminder,
}

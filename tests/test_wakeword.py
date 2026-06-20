"""Tests for the wake-word listener (openWakeWord and the mic are stubbed)."""
import numpy as np

from jarvis import wakeword
from jarvis.config import Config


class _FakeStream:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, n):
        return np.zeros((n, 1), dtype="int16"), False


class _FakeModel:
    def __init__(self, score):
        self.score = score
        self.calls = 0

    def reset(self):
        pass

    def predict(self, audio):
        self.calls += 1
        return {"hey_jarvis": self.score}


def test_wake_triggers_above_threshold(monkeypatch):
    import sounddevice

    monkeypatch.setattr(sounddevice, "InputStream", _FakeStream)
    cfg = Config()
    cfg.wake_threshold = 0.5
    listener = wakeword.WakeWordListener(cfg)
    listener._model = _FakeModel(0.9)
    assert listener.wait_for_wake() is True


def test_below_threshold_then_stop(monkeypatch):
    import sounddevice

    monkeypatch.setattr(sounddevice, "InputStream", _FakeStream)
    cfg = Config()
    listener = wakeword.WakeWordListener(cfg)
    listener._model = _FakeModel(0.0)
    # should_stop fires immediately, so it returns without ever triggering.
    assert listener.wait_for_wake(should_stop=lambda: True) is False

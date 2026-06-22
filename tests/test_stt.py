"""Tests for the transcription filtering (the real Whisper model is stubbed)."""
from types import SimpleNamespace

import numpy as np

from jarvis.config import Config
from jarvis.stt import _HALLUCINATIONS, Transcriber


class _Seg:
    def __init__(self, text, no_speech_prob=0.1, avg_logprob=-0.3):
        self.text = text
        self.no_speech_prob = no_speech_prob
        self.avg_logprob = avg_logprob


class _FakeModel:
    def __init__(self, segments):
        self.segments = segments

    def transcribe(self, audio, **kwargs):
        return iter(self.segments), SimpleNamespace()


def _transcriber(segments):
    t = Transcriber(Config())
    t._model = _FakeModel(segments)  # pre-set so no real model loads
    return t


def _audio(seconds=1.0, sr=16000):
    return np.zeros(int(seconds * sr), dtype="float32")


def test_short_audio_returns_empty():
    assert _transcriber([]).transcribe(_audio(0.1)) == ""


def test_keeps_real_speech():
    t = _transcriber([_Seg("what time is it")])
    assert t.transcribe(_audio()) == "what time is it"


def test_drops_high_no_speech_prob():
    t = _transcriber([_Seg("you", no_speech_prob=0.9)])
    assert t.transcribe(_audio()) == ""


def test_drops_low_confidence_segment():
    t = _transcriber([_Seg("garbled noise", avg_logprob=-2.0)])
    assert t.transcribe(_audio()) == ""


def test_drops_known_hallucination_phrase():
    t = _transcriber([_Seg("Thank you.")])
    assert t.transcribe(_audio()) == ""


def test_hallucination_set_has_common_phantoms():
    assert "thank you" in _HALLUCINATIONS and "you" in _HALLUCINATIONS

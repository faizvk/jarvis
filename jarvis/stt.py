"""Offline speech-to-text using faster-whisper (CTranslate2).

The Whisper model is loaded lazily on first use so that importing Jarvis (and the
``--doctor`` check) stays fast and doesn't require the model weights up front.
"""
from __future__ import annotations

import threading

# Whisper tends to emit these canned phrases on near-silence; a transcript that
# reduces to one of them is treated as nothing said.
_HALLUCINATIONS = {
    "thank you", "thanks", "thank you.", "thanks for watching",
    "thank you for watching", "please subscribe", "you", "bye", "bye.",
    "okay", "uh", ".",
}


class Transcriber:
    def __init__(self, config):
        self.config = config
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        # Locked so a background warm-up and the first transcribe() can't both
        # construct the model (double-load / use of a half-built model).
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.config.stt_model,
                    device=self.config.stt_device,
                    compute_type=self.config.stt_compute,
                )
        return self._model

    def warm_up(self) -> None:
        """Load the model now, off the interactive path (best-effort)."""
        self._ensure_model()

    def transcribe(self, audio) -> str:
        if audio is None or len(audio) == 0:
            return ""
        # Ignore ultra-short blips (< ~0.2s); they're almost always noise.
        if len(audio) < int(0.2 * (self.config.sample_rate or 16000)):
            return ""
        model = self._ensure_model()
        segments, _info = model.transcribe(
            audio,
            language=self.config.language or None,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            beam_size=self.config.stt_beam_size,
        )
        kept = []
        for seg in segments:
            # Drop segments Whisper itself flags as likely non-speech / low-confidence.
            if getattr(seg, "no_speech_prob", 0.0) > 0.6:
                continue
            if getattr(seg, "avg_logprob", 0.0) < -1.0:
                continue
            piece = seg.text.strip()
            if piece:
                kept.append(piece)
        text = " ".join(kept).strip()
        # A transcript that is just a known filler phrase = silence.
        if text.lower().strip(" .!?,") in _HALLUCINATIONS:
            return ""
        return text


def build_transcriber(config) -> Transcriber:
    return Transcriber(config)

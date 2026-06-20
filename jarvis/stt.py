"""Offline speech-to-text using faster-whisper (CTranslate2).

The Whisper model is loaded lazily on first use so that importing Jarvis (and the
``--doctor`` check) stays fast and doesn't require the model weights up front.
"""
from __future__ import annotations


class Transcriber:
    def __init__(self, config):
        self.config = config
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.config.stt_model,
                device=self.config.stt_device,
                compute_type=self.config.stt_compute,
            )
        return self._model

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
            beam_size=self.config.stt_beam_size,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


def build_transcriber(config) -> Transcriber:
    return Transcriber(config)

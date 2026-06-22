"""Offline wake-word detection ("Hey Jarvis") via openWakeWord.

openWakeWord ships a pretrained ``hey_jarvis`` model that runs on onnxruntime, so
detection is fully offline and needs no API key. The model is loaded lazily (and
downloaded on first use) so importing this module stays cheap.
"""
from __future__ import annotations

_FRAME = 1280  # 80 ms @ 16 kHz — the chunk size openWakeWord expects


class WakeWordListener:
    def __init__(self, config):
        self.config = config
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from openwakeword.model import Model

            try:
                self._model = Model(
                    wakeword_models=[self.config.wake_model], inference_framework="onnx"
                )
            except Exception:
                # Models aren't present yet — download them and retry once.
                from openwakeword.utils import download_models

                download_models()
                self._model = Model(
                    wakeword_models=[self.config.wake_model], inference_framework="onnx"
                )
        return self._model

    def load(self) -> None:
        """Load the wake-word model now (raises if it can't be built/downloaded)."""
        self._ensure_model()

    def wait_for_wake(self, should_stop=None) -> bool:
        """Block until the wake word is heard. Returns False if ``should_stop`` fires."""
        import sounddevice as sd

        model = self._ensure_model()
        model.reset()
        threshold = self.config.wake_threshold
        key = self.config.wake_model

        with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=_FRAME) as stream:
            while True:
                if should_stop is not None and should_stop():
                    return False
                data, _overflow = stream.read(_FRAME)
                scores = model.predict(data[:, 0])
                score = scores.get(key)
                if score is None and scores:
                    score = max(scores.values())
                if score is not None and score >= threshold:
                    return True

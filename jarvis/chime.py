"""A short two-tone chime, played to acknowledge the wake word."""
from __future__ import annotations


def play_chime(sample_rate: int = 16000) -> None:
    """Play a brief rising chime. Never raises — audio is best-effort."""
    try:
        import numpy as np
        import sounddevice as sd

        def tone(freq: float, dur: float) -> "np.ndarray":
            t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False)
            wave = 0.25 * np.sin(2 * np.pi * freq * t)
            fade = int(0.005 * sample_rate)  # short fades to avoid clicks
            if fade > 0 and wave.size > 2 * fade:
                env = np.ones_like(wave)
                env[:fade] = np.linspace(0, 1, fade)
                env[-fade:] = np.linspace(1, 0, fade)
                wave *= env
            return wave.astype("float32")

        chime = np.concatenate([tone(660, 0.08), tone(880, 0.10)])
        sd.play(chime, samplerate=sample_rate, blocking=True)
    except Exception:
        pass

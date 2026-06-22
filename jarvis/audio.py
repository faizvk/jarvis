"""Microphone capture with simple energy-based voice-activity detection.

``record_utterance`` opens the default input device, waits for the user to start
speaking, then records until it hears a stretch of trailing silence (or hits the
maximum duration). The result is a mono float32 array in ``[-1, 1]`` at the
configured sample rate, ready to hand straight to faster-whisper.
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd

_BLOCK_SECONDS = 0.05  # 50 ms analysis blocks


def list_input_devices() -> list[str]:
    try:
        return [
            d["name"]
            for d in sd.query_devices()
            if d.get("max_input_channels", 0) > 0
        ]
    except Exception:
        return []


def record_utterance(config, on_speech_start=None) -> "np.ndarray":
    sr = int(config.sample_rate)
    block = max(1, int(sr * _BLOCK_SECONDS))
    silence_needed = int(config.silence_duration / _BLOCK_SECONDS)
    max_blocks = int(config.max_record_seconds / _BLOCK_SECONDS)
    min_blocks = int(config.min_record_seconds / _BLOCK_SECONDS)
    no_speech_timeout = int(8.0 / _BLOCK_SECONDS)  # give up if nobody speaks

    started_min = 2  # require ~2 loud blocks (~100ms) so a single pop isn't "speech"

    frames: list[np.ndarray] = []
    silent_run = 0
    speech_blocks = 0
    loud_run = 0
    started = False

    with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=block) as stream:
        for i in range(max_blocks):
            data, _overflow = stream.read(block)
            mono = data[:, 0].copy()
            rms = float(np.sqrt(np.mean(mono ** 2))) if mono.size else 0.0

            if rms >= config.silence_threshold:
                speech_blocks += 1
                loud_run += 1
                if not started and speech_blocks >= started_min:
                    started = True
                    if on_speech_start:
                        on_speech_start()
                if started:
                    frames.append(mono)
                    # Only a sustained run (~2 loud blocks) clears the trailing-silence
                    # countdown, so a lone noisy block in the tail can't keep recording.
                    if loud_run >= 2:
                        silent_run = 0
            elif started:
                loud_run = 0
                silent_run += 1
                frames.append(mono)
                if len(frames) >= min_blocks and silent_run >= silence_needed:
                    break

            # Independent guard: bail out if nobody ever starts speaking. Kept as a
            # top-level check (not an elif) so a stray loud block can't disable it.
            if not started and i >= no_speech_timeout:
                break

    if not frames:
        return np.zeros(0, dtype="float32")
    return np.concatenate(frames).astype("float32")

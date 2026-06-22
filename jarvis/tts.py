"""Offline text-to-speech using pyttsx3 (Windows SAPI5).

All speech goes through a single dedicated worker thread that owns one long-lived
engine. This matters on Windows: SAPI5 (via comtypes/pythoncom) must be driven on
a COM-initialised thread with a message pump, and ``runAndWait`` is not re-entrant.
Routing every utterance — including reminders fired from the scheduler's daemon
thread — through this one worker keeps COM on a single, correctly initialised
apartment and avoids the per-utterance engine churn that leaks SAPI handles.
"""
from __future__ import annotations

import queue
import threading


class Speaker:
    _SENTINEL = object()

    def __init__(self, rate: int = 178, voice_substring: str = ""):
        self.rate = rate
        self.voice_substring = (voice_substring or "").strip()
        self._queue: "queue.Queue" = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="jarvis-tts", daemon=True)
        self._started = False
        self._start_lock = threading.Lock()

    # --- worker --------------------------------------------------------------
    def _start(self) -> None:
        with self._start_lock:
            if not self._started:
                self._thread.start()
                self._started = True

    def _build_engine(self):
        import pyttsx3

        engine = pyttsx3.init()
        try:
            engine.setProperty("rate", self.rate)
        except Exception:
            pass
        if self.voice_substring:
            needle = self.voice_substring.lower()
            for voice in engine.getProperty("voices"):
                if needle in (voice.name or "").lower():
                    engine.setProperty("voice", voice.id)
                    break
        return engine

    def _run(self) -> None:
        # SAPI5 needs COM initialised on this thread (single-threaded apartment).
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception:
            pythoncom = None  # type: ignore

        try:
            engine = self._build_engine()
        except Exception:
            engine = None  # speech disabled; callers still print their text

        while True:
            item = self._queue.get()
            if item is self._SENTINEL:
                break
            text, done = item
            try:
                if engine is None:
                    engine = self._build_engine()  # self-heal after a prior failure
                engine.say(text)
                engine.runAndWait()
            except Exception:
                # A broken/wedged engine: drop it so the next utterance rebuilds it
                # instead of every future turn silently failing.
                try:
                    if engine is not None:
                        engine.stop()
                except Exception:
                    pass
                engine = None
            finally:
                if done is not None:
                    done.set()

        try:
            if engine is not None:
                engine.stop()
        except Exception:
            pass
        try:
            if pythoncom is not None:
                pythoncom.CoUninitialize()
        except Exception:
            pass

    # --- public API ----------------------------------------------------------
    def say(self, text: str, block: bool = True) -> None:
        """Speak ``text``. Blocks until spoken when ``block`` is true.

        Safe to call from any thread; reminders use ``block=False`` so the
        scheduler thread is never held up.
        """
        text = (text or "").strip()
        if not text:
            return
        self._start()
        done = threading.Event() if block else None
        self._queue.put((text, done))
        if done is not None:
            # Bounded so a wedged engine can't stall the turn for a full minute;
            # the worker rebuilds the engine after a failure.
            done.wait(timeout=15)

    def stop(self) -> None:
        if self._started:
            self._queue.put(self._SENTINEL)
            self._thread.join(timeout=3)


def build_speaker(config) -> Speaker:
    return Speaker(config.tts_rate, config.tts_voice)

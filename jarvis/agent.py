"""The Jarvis agent: ties the LLM, tools, speech, and the interaction loops together."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from .config import Config, load_config
from .llm import OllamaClient, OllamaError
from .prompts import system_prompt
from .tools import TOOLS_SCHEMA, ToolContext, dispatch
from .tools.reminders import Scheduler

MAX_TOOL_ITERATIONS = 6
_EXIT_WORDS = {"quit", "exit", "goodbye", "good bye", "stop jarvis", "shut down"}


class Jarvis:
    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self.client = OllamaClient(
            self.config.host,
            self.config.model,
            self.config.temperature,
            keep_alive=self.config.keep_alive,
            num_ctx=self.config.num_ctx,
        )
        self.speaker = None        # built on demand for voice mode
        self.transcriber = None
        self.scheduler = Scheduler(
            self._announce, str(Path(self.config.state_dir) / "reminders.json")
        )
        self.scheduler.start()
        self.messages: list[dict] = [{
            "role": "system",
            "content": system_prompt(
                self.config.assistant_name,
                datetime.now().strftime("%A %B %d %Y %I:%M %p"),
            ),
        }]

    # --- output --------------------------------------------------------------
    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        print(f"{self.config.assistant_name}: {text}")
        if self.speaker:
            try:
                self.speaker.say(text)
            except Exception:
                pass

    def _announce(self, text: str) -> None:
        """Scheduler callback: surface a fired reminder/timer.

        Runs on the scheduler's daemon thread, so it must never block or raise.
        Speech is queued (non-blocking) and the text is always printed even if
        text-to-speech is unavailable, so a fired reminder can't be lost.
        """
        print(f"\n>>> {text}")
        if self.speaker:
            try:
                self.speaker.say(text, block=False)
            except Exception:
                pass

    def _confirm(self, prompt: str) -> bool:
        print(f"\n[confirm] {prompt}\n          type 'y' to allow, anything else to cancel: ", end="", flush=True)
        if self.speaker:
            self.speaker.say(f"{prompt}. Type yes to allow.")
        try:
            answer = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

    def _context(self) -> ToolContext:
        return ToolContext(
            config=self.config,
            speaker=self.speaker,
            scheduler=self.scheduler,
            confirm=self._confirm,
            notify=self._announce,
        )

    # --- core reasoning loop -------------------------------------------------
    def handle_text(self, user_text: str) -> str:
        """Run one user turn through the model, executing any tool calls."""
        self.messages.append({"role": "user", "content": user_text})
        ctx = self._context()

        for _ in range(MAX_TOOL_ITERATIONS):
            message = self.client.chat(self.messages, tools=TOOLS_SCHEMA) or {}
            self.messages.append(message or {"role": "assistant", "content": ""})

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return (message.get("content") or "").strip()

            for call in tool_calls:
                fn = call.get("function", {}) or {}
                name = fn.get("name", "")
                arguments = fn.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except (ValueError, TypeError):
                        arguments = {}
                print(f"  [tool] {name}({arguments})")
                result = dispatch(name, arguments, ctx)
                # Ollama's chat API binds tool results by the "tool_name" field.
                self.messages.append({"role": "tool", "tool_name": name, "content": result})

        # Too many tool rounds — ask for a final answer with tools disabled.
        final = self.client.chat(self.messages) or {}
        return (final.get("content") or "").strip()

    # --- interaction loops ---------------------------------------------------
    def enable_voice(self) -> None:
        from .stt import build_transcriber
        from .tts import build_speaker

        self.speaker = build_speaker(self.config)
        self.transcriber = build_transcriber(self.config)
        # Load the speech model off the interactive path so the first utterance
        # isn't blocked on a model download/load after the user has spoken.
        threading.Thread(target=self.transcriber.warm_up, daemon=True).start()

    def _capture_one(self) -> str:
        """Record and transcribe a single utterance ('' if nothing was heard)."""
        from .audio import record_utterance

        print("Listening...")
        audio = record_utterance(self.config, on_speech_start=lambda: print("  (hearing you)"))
        return self.transcriber.transcribe(audio).strip()

    def _is_exit(self, text: str) -> bool:
        return text.lower().strip(" .!?") in _EXIT_WORDS

    def _handle_utterance(self, text: str) -> bool:
        """Act on one transcribed utterance. Returns False when Jarvis should quit."""
        if not text:
            print("  (didn't catch that — try again)")
            return True
        print(f"You: {text}")
        if self._is_exit(text):
            self.speak("Goodbye.")
            return False
        self._respond(text)
        return True

    def _warm_up_async(self) -> None:
        """Preload the LLM in the background so the first reply isn't a cold load."""
        print("Warming up the model...")
        threading.Thread(target=self.client.warm_up, daemon=True).start()

    def run_voice_loop(self) -> None:
        self._warm_up_async()
        self.enable_voice()
        try:
            if self.config.wake_mode == "wakeword":
                self._wake_loop()
            else:
                self._enter_loop()
        finally:
            self.scheduler.stop()

    def _enter_loop(self) -> None:
        name = self.config.assistant_name
        self.speak(f"{name} online. Press Enter and speak. Say goodbye, or press Control C, to quit.")
        while True:
            try:
                input("\n[Press Enter, then speak] ")
            except (EOFError, KeyboardInterrupt):
                break
            try:
                text = self._capture_one()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                print(f"  (audio error — {exc}; try again)")
                continue
            if not self._handle_utterance(text):
                break

    def _wake_loop(self) -> None:
        from .chime import play_chime
        from .wakeword import WakeWordListener

        name = self.config.assistant_name
        listener = WakeWordListener(self.config)
        print(f"Loading wake word '{self.config.wake_model}' (first run downloads it)...")
        self.speak(f"{name} online. Say, hey {name}, to wake me. Press Control C to quit.")
        while True:
            print(f"\nListening for 'Hey {name}'...  (Ctrl+C to quit)")
            try:
                woke = listener.wait_for_wake()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                print(f"  (wake-word error — {exc})")
                self.speak("My wake word detector couldn't start.")
                break
            if not woke:
                continue
            if self.config.wake_chime:
                play_chime(self.config.sample_rate)
            try:
                text = self._capture_one()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                print(f"  (audio error — {exc}; try again)")
                continue
            if not self._handle_utterance(text):
                break
            time.sleep(max(0.0, self.config.wake_cooldown))

    def run_text_loop(self) -> None:
        self._warm_up_async()
        name = self.config.assistant_name
        print(f"{name} (text mode). Type your message, or 'quit' to exit.")
        try:
            while True:
                try:
                    text = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not text:
                    continue
                if self._is_exit(text):
                    break
                self._respond(text)
        finally:
            self.scheduler.stop()

    def run_once(self, text: str) -> str:
        """Handle a single query (used by --once) and return the reply."""
        try:
            reply = self.handle_text(text)
            self.speak(reply)
            return reply
        finally:
            self.scheduler.stop()

    def _respond(self, text: str) -> None:
        try:
            reply = self.handle_text(text)
        except OllamaError as exc:
            self.speak(f"I couldn't reach my brain. {exc}")
            return
        if reply:
            self.speak(reply)

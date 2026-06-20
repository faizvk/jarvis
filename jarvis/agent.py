"""The Jarvis agent: ties the LLM, tools, speech, and the interaction loops together."""
from __future__ import annotations

import json
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
        self.client = OllamaClient(self.config.host, self.config.model, self.config.temperature)
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

    def run_voice_loop(self) -> None:
        from .audio import record_utterance

        self.enable_voice()
        name = self.config.assistant_name
        self.speak(f"{name} online. Press Enter and speak. Say goodbye, or press Control C, to quit.")
        while True:
            try:
                input("\n[Press Enter, then speak] ")
            except (EOFError, KeyboardInterrupt):
                break
            print("Listening...")
            try:
                audio = record_utterance(self.config, on_speech_start=lambda: print("  (hearing you)"))
                text = self.transcriber.transcribe(audio).strip()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                # A transient mic/STT glitch should skip the turn, not crash Jarvis.
                print(f"  (audio error — {exc}; try again)")
                continue
            if not text:
                print("  (didn't catch that — try again)")
                continue
            print(f"You: {text}")
            if text.lower().strip(" .!?") in _EXIT_WORDS:
                self.speak("Goodbye.")
                break
            self._respond(text)
        self.scheduler.stop()

    def run_text_loop(self) -> None:
        name = self.config.assistant_name
        print(f"{name} (text mode). Type your message, or 'quit' to exit.")
        while True:
            try:
                text = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in _EXIT_WORDS:
                break
            self._respond(text)
        self.scheduler.stop()

    def _respond(self, text: str) -> None:
        try:
            reply = self.handle_text(text)
        except OllamaError as exc:
            self.speak(f"I couldn't reach my brain. {exc}")
            return
        if reply:
            self.speak(reply)

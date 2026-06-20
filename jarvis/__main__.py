"""Command-line entry point for Jarvis.

Usage:
    python -m jarvis            # voice mode (press Enter, then speak)
    python -m jarvis --text     # type instead of speaking
    python -m jarvis --doctor   # check the setup and exit
    python -m jarvis --say "hi" # speak one phrase (TTS test) and exit
"""
from __future__ import annotations

import argparse
import sys

from .config import load_config
from .llm import OllamaClient


def _doctor(config) -> int:
    print("Jarvis doctor")
    print("=============")
    client = OllamaClient(config.host, config.model)
    reachable = client.is_available()
    print(f"[{'OK' if reachable else '!!'}] Ollama reachable at {config.host}")
    if reachable:
        models = client.available_models()
        print(f"      models pulled: {', '.join(models) or '(none)'}")
        present = client.has_model()
        print(f"[{'OK' if present else '!!'}] requested model '{config.model}' present")
        if not present:
            print(f"      fix: ollama pull {config.model}")
    else:
        print("      fix: install Ollama (winget install Ollama.Ollama), start it,")
        print(f"           then run: ollama pull {config.model}")

    try:
        from .audio import list_input_devices

        devices = list_input_devices()
        print(f"[{'OK' if devices else '!!'}] {len(devices)} microphone input device(s)")
        if devices:
            print(f"      e.g. {devices[0]}")
    except Exception as exc:
        print(f"[!!] audio backend failed to load: {exc}")

    try:
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        engine.stop()
        sample = ", ".join(v.name for v in voices[:4])
        print(f"[OK] {len(voices)} text-to-speech voice(s): {sample}")
    except Exception as exc:
        print(f"[!!] text-to-speech failed to init: {exc}")

    try:
        import faster_whisper  # noqa: F401

        print("[OK] faster-whisper is importable (model downloads on first use)")
    except Exception as exc:
        print(f"[!!] faster-whisper import failed: {exc}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jarvis", description="A local voice assistant powered by Ollama."
    )
    parser.add_argument("--text", action="store_true", help="Text mode: type instead of speaking.")
    parser.add_argument("--doctor", action="store_true", help="Check the setup and exit.")
    parser.add_argument("--config", help="Path to a config TOML file.")
    parser.add_argument("--model", help="Override the Ollama model for this run.")
    parser.add_argument("--say", metavar="TEXT", help="Speak one phrase (TTS test) and exit.")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.model:
        config.model = args.model

    if args.doctor:
        return _doctor(config)

    if args.say:
        from .tts import build_speaker

        build_speaker(config).say(args.say)
        return 0

    client = OllamaClient(config.host, config.model)
    if not client.is_available():
        print(f"[!] Can't reach Ollama at {config.host}.")
        print("    1) Install it:  winget install Ollama.Ollama")
        print(f"    2) Pull a model:  ollama pull {config.model}")
        print("    3) Make sure the Ollama app/server is running, then re-launch.")
        return 1
    if not client.has_model():
        print(f"[!] The model '{config.model}' isn't pulled yet.")
        print(f"    Run:  ollama pull {config.model}")
        available = client.available_models()
        if available:
            print(f"    Or pick one you already have: {', '.join(available)}")
        return 1

    # Imported here so --doctor/--say work even if optional deps are missing.
    from .agent import Jarvis

    jarvis = Jarvis(config)
    try:
        if args.text:
            jarvis.run_text_loop()
        else:
            jarvis.run_voice_loop()
    except KeyboardInterrupt:
        print("\nShutting down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

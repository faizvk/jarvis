"""Configuration loading for Jarvis.

Reads an optional TOML file (config.toml in the project root by default) and
overlays it on top of the built-in defaults. Every field has a sane default so
Jarvis runs with no config file at all.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

# Project root = the directory that contains the `jarvis` package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    # --- LLM (Ollama) ---
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    temperature: float = 0.6

    # --- Speech-to-text (faster-whisper) ---
    stt_model: str = "base.en"
    stt_device: str = "cpu"
    stt_compute: str = "int8"
    language: str = "en"

    # --- Audio capture ---
    sample_rate: int = 16000
    silence_threshold: float = 0.012
    silence_duration: float = 1.2
    max_record_seconds: float = 20.0
    min_record_seconds: float = 0.4

    # --- Text-to-speech (pyttsx3 / SAPI5) ---
    tts_rate: int = 178
    tts_voice: str = ""

    # --- Behaviour ---
    assistant_name: str = "Jarvis"
    wake_mode: str = "enter"   # "enter" | "hotkey"
    hotkey: str = "space"
    confirm_commands: bool = True
    search_results: int = 5

    # --- Paths (computed) ---
    state_dir: str = str(PROJECT_ROOT / "state")

    def ensure_dirs(self) -> None:
        Path(self.state_dir).mkdir(parents=True, exist_ok=True)


# Maps a (section, key) in the TOML file to a Config attribute name.
_TOML_MAP = {
    ("llm", "host"): "host",
    ("llm", "model"): "model",
    ("llm", "temperature"): "temperature",
    ("stt", "model"): "stt_model",
    ("stt", "device"): "stt_device",
    ("stt", "compute"): "stt_compute",
    ("stt", "language"): "language",
    ("audio", "sample_rate"): "sample_rate",
    ("audio", "silence_threshold"): "silence_threshold",
    ("audio", "silence_duration"): "silence_duration",
    ("audio", "max_record_seconds"): "max_record_seconds",
    ("audio", "min_record_seconds"): "min_record_seconds",
    ("tts", "rate"): "tts_rate",
    ("tts", "voice"): "tts_voice",
    ("behavior", "assistant_name"): "assistant_name",
    ("behavior", "wake_mode"): "wake_mode",
    ("behavior", "hotkey"): "hotkey",
    ("behavior", "confirm_commands"): "confirm_commands",
    ("behavior", "search_results"): "search_results",
}


def _find_config_file(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    # Only the real config is auto-discovered. config.example.toml is a template
    # and must never be loaded implicitly (its values would silently take effect).
    p = PROJECT_ROOT / "config.toml"
    return p if p.is_file() else None


def load_config(path: str | None = None) -> Config:
    """Load configuration, overlaying any TOML file onto the defaults."""
    cfg = Config()
    valid = {f.name for f in fields(Config)}

    cfg_file = _find_config_file(path)
    if cfg_file is not None:
        with open(cfg_file, "rb") as fh:
            data = tomllib.load(fh)
        for (section, key), attr in _TOML_MAP.items():
            if section in data and key in data[section] and attr in valid:
                setattr(cfg, attr, data[section][key])

    # Environment overrides (handy for quick experiments).
    if os.environ.get("JARVIS_MODEL"):
        cfg.model = os.environ["JARVIS_MODEL"]
    if os.environ.get("OLLAMA_HOST"):
        cfg.host = os.environ["OLLAMA_HOST"]

    cfg.ensure_dirs()
    return cfg

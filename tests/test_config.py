"""Tests for configuration loading."""
from pathlib import Path

from jarvis.config import Config, load_config


def test_defaults():
    c = Config()
    assert c.host.startswith("http")
    assert c.model
    assert c.confirm_commands is True
    assert c.sample_rate == 16000
    assert c.wake_mode in ("enter", "hotkey")


def test_load_config_returns_config_and_makes_state_dir():
    c = load_config()
    assert isinstance(c, Config)
    assert Path(c.state_dir).is_dir()


def test_toml_overlay(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        "[llm]\n"
        'model = "test-model"\n'
        "temperature = 0.1\n"
        "[behavior]\n"
        "confirm_commands = false\n"
        "search_results = 9\n",
        encoding="utf-8",
    )
    c = load_config(str(cfg))
    assert c.model == "test-model"
    assert c.temperature == 0.1
    assert c.confirm_commands is False
    assert c.search_results == 9


def test_env_override(monkeypatch):
    monkeypatch.setenv("JARVIS_MODEL", "env-model")
    c = load_config()
    assert c.model == "env-model"

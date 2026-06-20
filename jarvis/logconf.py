"""Application logging: a rotating file log under the state directory.

Logging is best-effort — if it can't be configured (e.g. the state dir is not
writable) Jarvis still runs, just without a log file.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(config) -> None:
    try:
        log_dir = Path(config.state_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        level = getattr(logging, str(config.log_level).upper(), logging.INFO)
        handler = RotatingFileHandler(
            log_dir / "jarvis.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(_FORMAT))
        root = logging.getLogger("jarvis")
        root.setLevel(level)
        root.handlers.clear()
        root.addHandler(handler)
    except Exception:
        pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"jarvis.{name}")

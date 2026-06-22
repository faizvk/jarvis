"""Thin client for the Ollama HTTP API with tool-calling support."""
from __future__ import annotations

import requests


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error."""


class OllamaClient:
    def __init__(self, host: str, model: str, temperature: float = 0.6, timeout: int = 120,
                 keep_alive: str = "30m", num_ctx: int = 4096):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx

    # --- availability checks -------------------------------------------------
    def is_available(self) -> bool:
        try:
            return requests.get(f"{self.host}/api/tags", timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def available_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except requests.RequestException:
            return []

    def has_model(self) -> bool:
        models = self.available_models()
        if self.model in models:
            return True
        # Tolerate a missing/extra tag (e.g. "llama3.2" matching "llama3.2:3b").
        bases = {m.split(":")[0] for m in models}
        return self.model.split(":")[0] in bases

    # --- chat ----------------------------------------------------------------
    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Send a chat request and return the assistant ``message`` dict.

        The returned dict has ``role`` and ``content`` and, when the model decides
        to call tools, a ``tool_calls`` list. Raises :class:`OllamaError` on failure.
        """
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,  # top-level: keeps the model warm in VRAM
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            raise OllamaError(str(data["error"]))
        return data.get("message", {}) if isinstance(data, dict) else {}

    def warm_up(self) -> None:
        """Preload the model into memory before the first real turn (best-effort)."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": self.temperature, "num_predict": 1},
        }
        try:
            requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        except requests.RequestException:
            pass  # warm-up is an optimisation; never fail startup on it

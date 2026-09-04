# providers/ollama_provider.py – Ollama Adapter (lokale Modelle, isoliert).
#
# Ollama läuft lokal (Default http://localhost:11434) und hat eine einfache
# HTTP-Chat-API. Kein API-Key nötig. Web-Suche wird NICHT unterstützt →
# sources bleibt leer (Agenten fallen dann auf extract_urls() zurück).
#
# Modellwahl:
#   - BLOG_OLLAMA_MODEL (optional) erzwingt ein konkretes Ollama-Modell
#     (z. B. "llama3.1", "mistral", "qwen2.5").
#   - Sonst wird der übergebene Modellname 1:1 verwendet.
#
# Ollama-Server-URL: OLLAMA_BASE_URL (Default http://localhost:11434).
import os

import requests

from .base import BaseProvider


def _base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


class OllamaProvider(BaseProvider):
    name = "ollama"

    def is_available(self) -> bool:
        # Ollama gilt als verfügbar, wenn der Server antwortet.
        try:
            r = requests.get(f"{_base_url()}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def resolve_model(self, model: str) -> str:
        override = os.getenv("BLOG_OLLAMA_MODEL", "").strip()
        if override:
            return override
        return model

    def chat(self,
             model: str,
             messages: list[dict],
             system: str = "",
             max_tokens: int = 4096,
             temperature: float | None = None,
             web_search: bool = False) -> tuple[str, list[str]]:
        # Ollama erwartet das System-Prompt als erste Nachricht.
        ollama_messages: list[dict] = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        ollama_messages.extend(messages)

        options: dict = {"num_predict": max_tokens}
        if temperature is not None:
            options["temperature"] = temperature

        payload = {
            "model": self.resolve_model(model),
            "messages": ollama_messages,
            "stream": False,
            "options": options,
        }

        r = requests.post(f"{_base_url()}/api/chat", json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()

        text = (data.get("message", {}).get("content", "") or "").strip()
        # Ollama liefert keine Suchquellen → leer (extract_urls greift).
        return text, []

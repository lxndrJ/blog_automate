# providers/mistral_provider.py – Mistral Adapter (isoliert).
#
# API-Endpunkte:
#   - Standard-Chat:  POST /v1/chat/completions
#   - Web-Suche:      POST /v1/conversations  (model + tools=[{"type":"web_search"}])
#
# Voraussetzungen:
#   - MISTRAL_API_KEY gesetzt
#   - `requests` installiert (steht in requirements.txt)
#   - Kein SDK-Import nötig → kein Import-Fehler mehr möglich
#
# Modellwahl:
#   - BLOG_MISTRAL_MODEL (optional) erzwingt einen konkreten Mistral-Modellnamen.
#   - Sonst werden bekannte Claude-Namen auf sinnvolle Mistral-Modelle gemappt.
import os
import re
import json
import logging

import requests

from .base import BaseProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.mistral.ai/v1"

# Claude-Namen → Mistral-Namen (Fallback-Mapping, falls kein Override gesetzt).
_MODEL_MAP = {
    "claude-haiku-4-5": "mistral-small-latest",
    "claude-3-5-haiku": "mistral-small-latest",
    "claude-sonnet-4-5": "mistral-medium-latest",
    "claude-3-5-sonnet": "mistral-medium-latest",
    "claude-opus-4-1": "mistral-large-latest",
    "claude-3-5-opus": "mistral-large-latest",
}


def _api_key() -> str:
    return os.getenv("MISTRAL_API_KEY", "").strip()


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def _extract_urls(text: str, limit: int = 10) -> list[str]:
    """URLs aus Freitext ziehen (Web-Suche-Quellen)."""
    urls: list[str] = []
    for m in re.findall(r"https?://\S+", text or ""):
        url = m.rstrip(".,;:)]}")
        if url not in urls:
            urls.append(url)
    return urls[:limit]


def _parse_conversation_outputs(outputs: list[dict]) -> tuple[str, list[str]]:
    """Antwort-Text und Quellen-URLs aus den outputs eines /v1/conversations-Response parsen.

    outputs enthält Einträge von Typ:
      - "message.output"  → die eigentliche Antwort (content = str oder list)
      - "tool.execution"  → Tool-Aufrufe (web_search-Ergebnisse)
      - "tool_reference"  → Quellen als Teil des content-Arrays
    """
    text_parts: list[str] = []
    sources: list[str] = []

    for entry in outputs:
        entry_type = entry.get("type", "")

        if entry_type == "message.output":
            content = entry.get("content", "")
            if isinstance(content, str):
                text_parts.append(content)
                # URLs im Text finden
                for url in _extract_urls(content):
                    if url not in sources:
                        sources.append(url)
            elif isinstance(content, list):
                for chunk in content:
                    if not isinstance(chunk, dict):
                        continue
                    chunk_type = chunk.get("type", "")
                    if chunk_type == "text":
                        text_parts.append(chunk.get("text", ""))
                        for url in _extract_urls(chunk.get("text", "")):
                            if url not in sources:
                                sources.append(url)
                    elif chunk_type == "tool_reference":
                        url = chunk.get("url", "")
                        if url and url not in sources:
                            sources.append(url)

    text = "\n".join(text_parts).strip()
    return text, sources[:10]


class MistralProvider(BaseProvider):
    name = "mistral"

    def is_available(self) -> bool:
        return bool(_api_key())

    def resolve_model(self, model: str) -> str:
        override = os.getenv("BLOG_MISTRAL_MODEL", "").strip()
        if override:
            return override
        return _MODEL_MAP.get(model, model)

    # ------------------------------------------------------------------
    # Haupt-Methoden
    # ------------------------------------------------------------------

    def chat(self,
             model: str,
             messages: list[dict],
             system: str = "",
             max_tokens: int = 4096,
             temperature: float | None = None,
             web_search: bool = False) -> tuple[str, list[str]]:
        """LLM-Call bei Mistral.

        - web_search=False → POST /v1/chat/completions
        - web_search=True  → POST /v1/conversations (mit tools=[{"type":"web_search"}])
        """
        resolved_model = self.resolve_model(model)

        if web_search:
            return self._chat_with_web_search(
                resolved_model, messages, system, max_tokens, temperature
            )
        return self._chat_standard(
            resolved_model, messages, system, max_tokens, temperature
        )

    # ------------------------------------------------------------------
    # Standard-Chat (ohne Web-Suche)
    # ------------------------------------------------------------------

    def _chat_standard(self, model: str, messages: list[dict],
                       system: str, max_tokens: int,
                       temperature: float | None) -> tuple[str, list[str]]:
        """POST /v1/chat/completions – klassischer Chat-Endpoint."""
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        body: dict = {
            "model": model,
            "messages": msgs,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            body["temperature"] = temperature

        resp = requests.post(
            f"{_BASE_URL}/chat/completions",
            headers=_headers(),
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        text = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()
        return text, []

    # ------------------------------------------------------------------
    # Web-Suche über /v1/conversations
    # ------------------------------------------------------------------

    def _chat_with_web_search(self, model: str, messages: list[dict],
                              system: str, max_tokens: int,
                              temperature: float | None) -> tuple[str, list[str]]:
        """Web-Suche über POST /v1/conversations.

        Kein Agent nötig – einfach model + tools + inputs senden.
        Die API führt die Web-Suche serverseitig aus und liefert
        die Antwort inkl. Quellen-URLs (tool_reference) zurück.
        """
        # User-Text extrahieren (letzte user-Nachricht)
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_text = content
                elif isinstance(content, list):
                    user_text = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                break

        # Fallback: komplette messages als JSON
        if not user_text:
            user_text = json.dumps(messages, ensure_ascii=False)

        body: dict = {
            "inputs": user_text,
            "model": model,
            "tools": [{"type": "web_search"}],
            "stream": False,
            "store": True,
            "completion_args": {
                "max_tokens": max_tokens,
                "top_p": 0.95,
            },
        }
        if temperature is not None:
            body["completion_args"]["temperature"] = temperature
        else:
            body["completion_args"]["temperature"] = 0.3

        if system:
            body["instructions"] = system

        resp = requests.post(
            f"{_BASE_URL}/conversations",
            headers=_headers(),
            json=body,
            timeout=120,
        )

        if resp.status_code != 200:
            # Fallback auf Standard-Chat (ohne Web-Suche)
            logger.warning(
                "Mistral /v1/conversations failed (HTTP %d): %s",
                resp.status_code, resp.text[:300],
            )
            return self._chat_standard(model, messages, system, max_tokens, temperature)

        data = resp.json()
        outputs = data.get("outputs", [])
        text, sources = _parse_conversation_outputs(outputs)

        # Falls keine structured outputs, aber usage vorhanden → evtl. im Text
        if not text:
            # Manchmal steckt die Antwort anders – versuchen, URLs aus dem Rohtext zu ziehen
            raw = json.dumps(data, ensure_ascii=False)
            sources = _extract_urls(raw)

        return text, sources

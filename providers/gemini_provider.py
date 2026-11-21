# providers/gemini_provider.py – Gemini Adapter (isoliert).
#
# API-Endpunkte (Generative Language API, REST – kein SDK nötig):
#   - Standard-Chat:  POST /v1beta/models/{model}:generateContent
#   - Web-Suche:      gleicher Endpoint mit tools=[{"google_search": {}}]
#
# Voraussetzungen:
#   - GEMINI_API_KEY (oder GOOGLE_API_KEY) gesetzt
#   - `requests` installiert (steht in requirements.txt)
#
# Modellwahl:
#   - BLOG_GEMINI_MODEL (optional) erzwingt einen konkreten Gemini-Modellnamen.
#   - Sonst werden bekannte Claude-Namen auf sinnvolle Gemini-Modelle gemappt.
import os
import logging

import requests

from .base import BaseProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Claude-Namen → Gemini-Namen (Fallback-Mapping, falls kein Override gesetzt).
_MODEL_MAP = {
    "claude-haiku-4-5": "gemini-2.5-flash",
    "claude-3-5-haiku": "gemini-2.5-flash",
    "claude-sonnet-4-5": "gemini-2.5-pro",
    "claude-3-5-sonnet": "gemini-2.5-pro",
    "claude-opus-4-1": "gemini-2.5-pro",
    "claude-3-5-opus": "gemini-2.5-pro",
}


def _api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )


def _contents(messages: list[dict], system: str) -> tuple[list[dict], str]:
    """messages → Gemini-contents (role "user"/"model") + System-Prompt."""
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        gemini_role = "model" if role == "assistant" else "user"
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"].append({"text": content})
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return contents, (system or "").strip()


def _extract_text(candidates: list[dict]) -> str:
    for cand in candidates or []:
        parts = (cand.get("content") or {}).get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
        if texts:
            return "\n".join(texts).strip()
    return ""


def _extract_sources(data: dict, limit: int = 10) -> list[str]:
    """Quellen-URLs aus den groundingMetadata des Responses ziehen."""
    sources: list[str] = []
    for cand in data.get("candidates", []) or []:
        meta = cand.get("groundingMetadata") or {}
        for chunk in meta.get("groundingChunks", []) or []:
            uri = ((chunk.get("web") or {}).get("uri") or "").strip()
            if uri and uri not in sources:
                sources.append(uri)
        for sup in meta.get("webSearchQueries") or []:
            if sup not in sources:
                sources.append(sup)
    return sources[:limit]


class GeminiProvider(BaseProvider):
    name = "gemini"

    def is_available(self) -> bool:
        return bool(_api_key())

    def resolve_model(self, model: str) -> str:
        override = os.getenv("BLOG_GEMINI_MODEL", "").strip()
        if override:
            return override
        return _MODEL_MAP.get(model, model)

    def chat(self,
             model: str,
             messages: list[dict],
             system: str = "",
             max_tokens: int = 4096,
             temperature: float | None = None,
             web_search: bool = False) -> tuple[str, list[str]]:
        """LLM-Call bei Gemini.

        - web_search=True → tools=[{"google_search": {}}] (serverseitige Suche)
        """
        resolved_model = self.resolve_model(model)
        contents, system_prompt = _contents(messages, system)

        body: dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
            },
        }
        if temperature is not None:
            body["generationConfig"]["temperature"] = temperature
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if web_search:
            body["tools"] = [{"google_search": {}}]

        resp = requests.post(
            f"{_BASE_URL}/models/{resolved_model}:generateContent",
            headers={"x-goog-api-key": _api_key()},
            json=body,
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gemini generateContent failed (HTTP {resp.status_code}): "
                f"{resp.text[:300]}"
            )
        data = resp.json()

        text = _extract_text(data.get("candidates", []))
        sources = _extract_sources(data) if web_search else []

        if not text:
            logger.warning(
                "Gemini: leere Antwort (finishReason=%s)",
                (data.get("candidates") or [{}])[0].get("finishReason", "?"),
            )
        return text, sources

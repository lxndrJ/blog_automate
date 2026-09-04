# llm_client.py – zentraler LLM-Zugang: Anthropic (Claude) als einziger Provider.
#
# Alle Agents/Module rufen stattdessen `llm_client.chat(...)` auf.
#
# Provider:
#   Anthropic (wenn ANTHROPIC_API_KEY gesetzt)
#
# Modellnamen: In config.py stehen Claude-Modellnamen (z. B. "claude-haiku-4-5").
# Sie werden 1:1 an die Anthropic-API übergeben.

import os
import re

# ── Key ─────────────────────────────────────────────────────────────────────

def anthropic_api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "").strip()


def require_provider() -> None:
    """Fehlermeldung, wenn kein API-Key vorhanden ist."""
    if not anthropic_api_key():
        raise RuntimeError(
            "ANTHROPIC_API_KEY ist nicht gesetzt. "
            "Setze den API-Key, um die LLM-Pipeline zu starten."
        )


def provider_status() -> str:
    """Kurze Beschreibung der Konfiguration (für Logs)."""
    if anthropic_api_key():
        return "Anthropic (Claude)"
    return "KEIN Provider konfiguriert"


# ── Provider-Implementierung ────────────────────────────────────────────────

def _chat_anthropic(model: str, messages: list[dict], system: str,
                    max_tokens: int, temperature: float | None,
                    web_search: bool) -> tuple[str, list[str]]:
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key())

    kwargs: dict = {}
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature
    if web_search:
        kwargs["tools"] = [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
        ]

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        **kwargs,
    )

    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    sources: list[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "web_search_tool_result":
            for hit in getattr(block, "content", []) or []:
                url = getattr(hit, "url", None)
                if url and url not in sources:
                    sources.append(url)

    return text, sources[:10]


# ── Öffentliche API ─────────────────────────────────────────────────────────

def chat(model: str,
         messages: list[dict],
         system: str = "",
         max_tokens: int = 4096,
         temperature: float | None = None,
         web_search: bool = False) -> tuple[str, list[str]]:
    """LLM-Call über Anthropic (Claude).

    Args:
        model:        Claude-Modellname (z. B. "claude-haiku-4-5")
        messages:     [{"role": "user", "content": "..."}, ...]
        system:       System-Prompt (optional)
        max_tokens:   Max. Antwort-Länge
        temperature:  Sampling-Temperatur (None = Provider-Default)
        web_search:   Server-seitige Web-Suche aktivieren

    Returns:
        (text, sources) – sources ist eine Liste von URLs (nur bei web_search)
    """
    require_provider()
    return _chat_anthropic(model, messages, system,
                           max_tokens, temperature, web_search)


def extract_urls(text: str, limit: int = 10) -> list[str]:
    """Helper: URLs aus Freitext ziehen (Fallback, falls keine Search-Quellen)."""
    urls: list[str] = []
    for m in re.findall(r"https?://\S+", text or ""):
        url = m.rstrip(".,;:)]}")
        if url not in urls:
            urls.append(url)
    return urls[:limit]

# llm_client.py – zentrale, STABLE LLM-Schnittstelle (dünne Fassade).
#
# Alle Agents/Module rufen NUR `llm_client.chat(...)` auf. Die eigentliche
# Provider-Logik (Anthropic, Mistral, Ollama) lebt isoliert in providers/
# und wird vom router.py gewählt – inkl. Fallback. So bricht ein defekter
# Provider die anderen nicht.
#
# Routing (Env BLOG_LLM_PROVIDER):
#   - "auto" (Default): anthropic → mistral → ollama, nächster verfügbarer wird genutzt
#   - "anthropic" | "mistral" | "ollama": nur dieser Provider
#
# Modellnamen in config.py bleiben Claude-Namen. Jeder Provider übersetzt sie
# selbst (resolve_model) oder nutzt einen eigenen Override:
#   BLOG_MISTRAL_MODEL, BLOG_OLLAMA_MODEL, OLLAMA_BASE_URL.
import re

import router


def provider_status() -> str:
    """Kurze Beschreibung der Konfiguration (für Logs)."""
    return router.provider_status()


def require_provider() -> None:
    """Fehler, wenn kein Provider verfügbar ist (Backward-Compat-Helper)."""
    if not router.available_providers():
        raise RuntimeError(
            "Kein LLM-Provider konfiguriert/verfügbar. Setze z. B. "
            "ANTHROPIC_API_KEY oder starte Ollama (BLOG_LLM_PROVIDER=ollama)."
        )


def chat(model: str,
         messages: list[dict],
         system: str = "",
         max_tokens: int = 4096,
         temperature: float | None = None,
         web_search: bool = False) -> tuple[str, list[str]]:
    """LLM-Call über den (automatisch gewählten) Provider.

    Signatur unverändert – Agenten merken nichts vom Provider-Wechsel.

    Args:
        model:        Modellname (Claude-Name; Provider übersetzt selbst)
        messages:     [{"role": "user", "content": "..."}, ...]
        system:       System-Prompt (optional)
        max_tokens:   Max. Antwort-Länge
        temperature:  Sampling-Temperatur (None = Provider-Default)
        web_search:   Server-seitige Web-Suche aktivieren (falls unterstützt)

    Returns:
        (text, sources) – sources ist eine Liste von URLs (leer, wenn keine)
    """
    return router.chat(model, messages, system,
                       max_tokens, temperature, web_search)


def extract_urls(text: str, limit: int = 10) -> list[str]:
    """Helper: URLs aus Freitext ziehen (Fallback, falls keine Search-Quellen)."""
    urls: list[str] = []
    for m in re.findall(r"https?://\S+", text or ""):
        url = m.rstrip(".,;:)]}")
        if url not in urls:
            urls.append(url)
    return urls[:limit]

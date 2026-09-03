# llm_client.py – zentraler LLM-Zugang: Mistral primär, Anthropic als Fallback.
#
# Alle Agents/Module rufen stattdessen `llm_client.chat(...)` auf.
#
# Priorität:
#   1. Mistral  (wenn MISTRAL_API_KEY gesetzt)
#   2. Anthropic (wenn ANTHROPIC_API_KEY gesetzt)
#
# Fällt Mistral aus (Netzwerk, Rate-Limit, Auth-Fehler), wird derselbe Call
# automatisch über Anthropic wiederholt. Ist nur ein Key gesetzt, läuft
# einfach nur dieser Provider.
#
# Modell-Mapping: In config.py dürfen weiterhin Claude-Modellnamen stehen
# (z. B. "claude-haiku-4-5") – bei Mistral werden sie automatisch auf die
# passende Mistral-Klasse gemappt. Oder man setzt direkt einen Mistral-Namen
# (z. B. BLOG_DRAFTER_MODEL=mistral-medium-latest).

import os
import re
import sys

# ── Keys ────────────────────────────────────────────────────────────────────

def mistral_api_key() -> str:
    return os.getenv("MISTRAL_API_KEY", "").strip()


def anthropic_api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "").strip()


def available_providers() -> list[str]:
    """Gibt die verfügbaren Provider in Prioritätsreihenfolge zurück."""
    providers = []
    if mistral_api_key():
        providers.append("mistral")
    if anthropic_api_key():
        providers.append("anthropic")
    return providers


def require_provider() -> None:
    """Fehlermeldung, wenn gar kein API-Key vorhanden ist."""
    if not available_providers():
        raise RuntimeError(
            "Kein LLM-API-Key gesetzt. Setze mindestens MISTRAL_API_KEY "
            "(primär) oder ANTHROPIC_API_KEY (Fallback)."
        )


def provider_status() -> str:
    """Kurze Beschreibung der Konfiguration (für Logs)."""
    providers = available_providers()
    if len(providers) == 2:
        return "Mistral (Anthropic als Fallback)"
    if providers:
        return providers[0]
    return "KEIN Provider konfiguriert"


# ── Modell-Mapping ──────────────────────────────────────────────────────────

# Claude-Klasse → passende Mistral-Klasse
_MISTRAL_CLASS_MAP = {
    "haiku":  os.getenv("BLOG_MISTRAL_HAIKU",  "mistral-small"),
    "sonnet": os.getenv("BLOG_MISTRAL_SONNET", "mistral-medium"),
    "opus":   os.getenv("BLOG_MISTRAL_OPUS",   "mistral-large"),
}

# Mistral model names -> Claude model names (for Anthropic fallback)
_MISTRAL_TO_CLAUDE_MAP = {
    "mistral-large": os.getenv("BLOG_ANTHROPIC_LARGE", "claude-3-5-sonnet-20250620"),
    "mistral-medium": os.getenv("BLOG_ANTHROPIC_MEDIUM", "claude-3-5-sonnet-20250620"),
    "mistral-small": os.getenv("BLOG_ANTHROPIC_SMALL", "claude-3-5-sonnet-20250620"),
}


def map_model_to_claude(model: str) -> str:
    """Mappt ein Mistral-Modell auf einen Claude-Modellnamen (fur Anthropic)."""
    m = (model or "").lower()
    # Direct mapping for known Mistral models
    for mistral_name, claude_name in _MISTRAL_TO_CLAUDE_MAP.items():
        if mistral_name in m:
            return claude_name
    # If it's already a Claude model, return as-is
    if "claude" in m:
        return model
    # Fallback to a sensible default
    return os.getenv("BLOG_ANTHROPIC_DEFAULT_MODEL", "claude-3-5-sonnet-20250620")



def map_model_to_mistral(model: str) -> str:
    """Mappt ein (ggf. Claude-)Modell auf einen Mistral-Modellnamen."""
    m = (model or "").lower()
    if "mistral" in m or "open-mistral" in m:
        return model  # bereits ein Mistral-Modell
    for key, mistral_model in _MISTRAL_CLASS_MAP.items():
        if key in m:
            return mistral_model
    return os.getenv("BLOG_MISTRAL_DEFAULT_MODEL", "mistral-large-latest")


# ── Provider-Implementierungen ──────────────────────────────────────────────

def _chat_mistral(model: str, messages: list[dict], system: str,
                  max_tokens: int, temperature: float | None,
                  web_search: bool) -> tuple[str, list[str]]:
    from mistralai.client import Mistral  # Lazy-Import: läuft auch ohne Installation
    from mistralai.client.models import WebSearchTool

    client = Mistral(api_key=mistral_api_key())

    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    kwargs: dict = {}
    if temperature is not None:
        kwargs["temperature"] = temperature

    if web_search:
        kwargs["tools"] = [WebSearchTool()]

    resp = client.chat.complete(
        model=model,
        messages=all_messages,
        max_tokens=max_tokens,
        **kwargs,
    )

    # Get the assistant message from the response
    choice = resp.choices[0]
    assistant_msg = choice.message
    
    # Handle content which can be a string or a list of content chunks
    if assistant_msg is None:
        text = ""
    elif isinstance(assistant_msg.content, str):
        text = assistant_msg.content
    elif isinstance(assistant_msg.content, list):
        # Content is a list of chunks, extract text from TextChunk and ReferenceChunk
        text_parts = []
        for chunk in assistant_msg.content:
            if hasattr(chunk, 'text') and chunk.text:
                text_parts.append(chunk.text)
            elif hasattr(chunk, 'type') and chunk.type == 'reference':
                # ReferenceChunk - skip the reference itself, just get text
                pass
        text = "".join(text_parts)
    else:
        text = str(assistant_msg.content or "")
    
    text = text.strip()
    
    # Extract sources from references in the content
    sources: list[str] = []
    if assistant_msg and hasattr(assistant_msg, 'content') and isinstance(assistant_msg.content, list):
        for chunk in assistant_msg.content:
            if hasattr(chunk, 'type') and chunk.type == 'reference' and hasattr(chunk, 'reference_ids'):
                # Reference chunks may contain reference IDs
                # We need to extract URLs from the response if available
                pass
    
    # Also check for tool_calls which might contain web search results
    if assistant_msg and hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
        for tool_call in assistant_msg.tool_calls:
            if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                # Try to extract URLs from tool call arguments
                import json
                try:
                    args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                    if isinstance(args, dict):
                        for key, value in args.items():
                            if isinstance(value, str) and ('http://' in value or 'https://' in value):
                                if value not in sources:
                                    sources.append(value)
                except (json.JSONDecodeError, AttributeError):
                    pass
    
    # Extract sources from tool_results if present in response
    if hasattr(resp, 'tool_results') and resp.tool_results:
        for tool_result in resp.tool_results:
            if hasattr(tool_result, 'content') and tool_result.content:
                for item in tool_result.content:
                    if hasattr(item, 'url'):
                        url = item.url
                        if url and url not in sources:
                            sources.append(url)
    
    return text, sources


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
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]

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
    """LLM-Call mit Provider-Fallback.

    Args:
        model:        Modellname (Claude- oder Mistral-Namen; wird gemappt)
        messages:     [{"role": "user", "content": "..."}, ...]
        system:       System-Prompt (optional)
        max_tokens:   Max. Antwort-Länge
        temperature:  Sampling-Temperatur (None = Provider-Default)
        web_search:   Server-seitige Web-Suche aktivieren

    Returns:
        (text, sources) – sources ist eine Liste von URLs (nur bei web_search)
    """
    providers = available_providers()
    if not providers:
        require_provider()

    errors: list[str] = []
    for i, provider in enumerate(providers):
        try:
            if provider == "mistral":
                return _chat_mistral(map_model_to_mistral(model), messages,
                                     system, max_tokens, temperature, web_search)
            elif provider == "anthropic":
                return _chat_anthropic(map_model_to_claude(model), messages, system,
                                       max_tokens, temperature, web_search)
        except Exception as e:
            errors.append(f"{provider}: {e}")
            if i + 1 < len(providers):
                next_provider = providers[i + 1]
                print(f"      ⚠ {provider} fehlgeschlagen ({e}) – "
                      f"fallback auf {next_provider} …", file=sys.stderr)

    raise RuntimeError("Alle LLM-Provider fehlgeschlagen:\n"
                       + "\n".join(f"  - {e}" for e in errors))


def extract_urls(text: str, limit: int = 10) -> list[str]:
    """Helper: URLs aus Freitext ziehen (Fallback, falls keine Search-Quellen)."""
    urls: list[str] = []
    for m in re.findall(r"https?://\S+", text or ""):
        url = m.rstrip(".,;:)]}")
        if url not in urls:
            urls.append(url)
    return urls[:limit]

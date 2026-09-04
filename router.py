# router.py – wählt den aktiven LLM-Provider und regelt Fallbacks.
#
# Routing-Regeln (Env: BLOG_LLM_PROVIDER):
#   - "anthropic" / "mistral" / "ollama" → NUR dieser Provider.
#     Ist er nicht verfügbar → klare Fehlermeldung (kein stiller Fallback).
#   - "auto" (Default) → Provider in Prioritätsreihenfolge versuchen:
#       anthropic → mistral → ollama
#     Ein defekter Provider (Key fehlt, SDK fehlt, API-Fehler, Server down)
#     bricht NICHT die anderen: der nächste verfügbare wird genutzt.
#
# Agenten rufen nie den Router direkt an, sondern llm_client.chat().
import os

from providers.anthropic_provider import AnthropicProvider
from providers.mistral_provider import MistralProvider
from providers.ollama_provider import OllamaProvider

# Prioritätsreihenfolge für "auto" (Claude = stabiler Default zuerst).
_PRIORITY = [AnthropicProvider, MistralProvider, OllamaProvider]


def _requested() -> str:
    return os.getenv("BLOG_LLM_PROVIDER", "auto").strip().lower()


def _ordered_providers():
    requested = _requested()
    by_name = {c.name: c for c in _PRIORITY}
    if requested in by_name:
        return [by_name[requested]()], requested  # Instanz anlegen, nicht Klasse
    return [c() for c in _PRIORITY], requested


def available_providers() -> list[str]:
    """Namen aller aktuell nutzbaren Provider (für Logs/Status)."""
    names = []
    for cls in _PRIORITY:
        p = cls()
        try:
            if p.is_available():
                names.append(p.name)
        except Exception:
            pass
    return names


def provider_status() -> str:
    """Kurze Beschreibung der Konfiguration (für Logs)."""
    requested = _requested()
    avail = available_providers()
    if not avail:
        return "KEIN LLM-Provider verfügbar (Key/SDK/Server fehlt)"
    if requested == "auto":
        return f"auto → verfügbar: {', '.join(avail)}"
    if requested in avail:
        return requested
    return f"gewünscht: {requested} (NICHT verfügbar) – verfügbar: {', '.join(avail)}"


def chat(model: str,
         messages: list[dict],
         system: str = "",
         max_tokens: int = 4096,
         temperature: float | None = None,
         web_search: bool = False) -> tuple[str, list[str]]:
    """LLM-Call über den (automatisch gewählten) Provider.

    Gleiche Signatur wie bisherige llm_client.chat() – Agenten merken nichts.
    """
    providers, requested = _ordered_providers()
    errors: list[str] = []

    for p in providers:
        try:
            if not p.is_available():
                msg = f"Provider '{p.name}' nicht verfügbar (Key/SDK/Server fehlt)."
                errors.append(msg)
                if requested != "auto":
                    break
                continue
        except Exception as e:  # is_available selbst darf nichts brechen
            errors.append(f"Provider '{p.name}' is_available-Fehler: {e}")
            if requested != "auto":
                break
            continue

        try:
            return p.chat(model, messages, system,
                          max_tokens, temperature, web_search)
        except Exception as e:
            errors.append(f"Provider '{p.name}' fehlgeschlagen: {e}")
            if requested != "auto":
                # Explizit gewählter Provider → Fehler klar weiterreichen.
                raise RuntimeError(
                    f"Provider '{p.name}' fehlgeschlagen: {e}"
                ) from e
            # auto-Modus: nächsten Provider versuchen.
            continue

    if errors:
        raise RuntimeError(
            "Kein LLM-Provider hat den Call erfolgreich ausgeführt.\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    raise RuntimeError(
        "Kein LLM-Provider konfiguriert/verfügbar. Setze z. B. ANTHROPIC_API_KEY "
        "oder starte Ollama (BLOG_LLM_PROVIDER=ollama)."
    )

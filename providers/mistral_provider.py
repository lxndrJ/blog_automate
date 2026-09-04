# providers/mistral_provider.py – Mistral Adapter (isoliert).
#
# Mistral hat eine andere API als Anthropic (Chat-Format, anderes
# Web-Search-Handling). Alles Mistral-spezifische lebt hier in EINER Datei.
#
# Voraussetzungen:
#   - MISTRAL_API_KEY gesetzt
#   - Paket `mistralai` installiert (wird lazy importiert, bricht nichts,
#     wenn es fehlt)
#
# Modellwahl:
#   - BLOG_MISTRAL_MODEL (optional) erzwingt einen konkreten Mistral-Modellnamen.
#   - Sonst werden bekannte Claude-Namen auf sinnvolle Mistral-Modelle gemappt.
import os

from .base import BaseProvider

# Claude-Namen → Mistral-Namen (Fallback-Mapping, falls kein Override gesetzt).
_MODEL_MAP = {
    "claude-haiku-4-5": "mistral-small-latest",
    "claude-3-5-haiku": "mistral-small-latest",
    "claude-sonnet-4-5": "mistral-large-latest",
    "claude-3-5-sonnet": "mistral-large-latest",
    "claude-opus-4-1": "mistral-large-latest",
}


def _api_key() -> str:
    return os.getenv("MISTRAL_API_KEY", "").strip()


class MistralProvider(BaseProvider):
    name = "mistral"

    def is_available(self) -> bool:
        if not _api_key():
            return False
        try:
            import mistralai  # noqa: F401
            return True
        except Exception:
            return False

    def resolve_model(self, model: str) -> str:
        override = os.getenv("BLOG_MISTRAL_MODEL", "").strip()
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
        import mistralai

        client = mistralai.MistralClient(api_key=_api_key())

        kwargs: dict = {}
        if system:
            kwargs["system_prompt"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        if web_search:
            # Mistral: Web-Suche als Tool, max 5 Aufrufe.
            kwargs["tools"] = [{"type": "web_search", "max_uses": 5}]

        resp = client.chat(
            model=self.resolve_model(model),
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        )

        text = (getattr(resp.choices[0].message, "content", "") or "").strip()

        # Quellen: Mistral liefert sie (falls Web-Suche) in `search_results`.
        sources: list[str] = []
        for hit in getattr(resp, "search_results", None) or []:
            url = getattr(hit, "url", None)
            if url and url not in sources:
                sources.append(url)

        return text, sources[:10]

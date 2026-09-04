# providers/anthropic_provider.py – Anthropic (Claude) Adapter.
#
# 1:1 der bisherige, funktionierende Code – nur umgezogen, nicht geändert.
# Läuft als stabiler Default-Provider.
import os

from .base import BaseProvider


def _api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "").strip()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def is_available(self) -> bool:
        if not _api_key():
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except Exception:
            return False

    def chat(self,
             model: str,
             messages: list[dict],
             system: str = "",
             max_tokens: int = 4096,
             temperature: float | None = None,
             web_search: bool = False) -> tuple[str, list[str]]:
        import anthropic

        client = anthropic.Anthropic(api_key=_api_key())

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
            model=self.resolve_model(model),
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

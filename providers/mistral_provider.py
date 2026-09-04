# providers/mistral_provider.py – Mistral Adapter (isoliert).
#
# Mistral hat eine andere API als Anthropic:
#   - Standard-Chat:  client.chat.complete(...)
#   - Web-Suche:      über die Agents API (client.beta.agents.create → client.agents.complete)
#                     (läuft intern über /v1/conversations)
#
# Voraussetzungen:
#   - MISTRAL_API_KEY gesetzt
#   - Paket `mistralai` (>=2.0) installiert (wird lazy importiert, bricht nichts,
#     wenn es fehlt)
#
# Modellwahl:
#   - BLOG_MISTRAL_MODEL (optional) erzwingt einen konkreten Mistral-Modellnamen.
#   - Sonst werden bekannte Claude-Namen auf sinnvolle Mistral-Modelle gemappt.
import os
import re

from .base import BaseProvider

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


def _import_mistral():
    """Mistral-Client importieren (kompatibel zu SDK 1.x und 2.x).

    - mistralai >= 2.0:  from mistralai.client import Mistral
    - mistralai <  2.0:  from mistralai import Mistral
    """
    try:
        from mistralai.client import Mistral  # SDK >= 2.0
        return Mistral
    except Exception:
        from mistralai import Mistral  # SDK < 2.0
        return Mistral


def _extract_urls(text: str, limit: int = 10) -> list[str]:
    """URLs aus Freitext ziehen (Web-Suche-Quellen)."""
    urls: list[str] = []
    for m in re.findall(r"https?://\S+", text or ""):
        url = m.rstrip(".,;:)]}")
        if url not in urls:
            urls.append(url)
    return urls[:limit]


class MistralProvider(BaseProvider):
    name = "mistral"

    def is_available(self) -> bool:
        if not _api_key():
            return False
        try:
            _import_mistral()  # noqa: F841
            return True
        except Exception:
            return False

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

        - web_search=False → Standard-Chat-Endpoint (client.chat.complete)
        - web_search=True  → Agents API (client.beta.agents.create → client.agents.complete)
          mit tools=[{"type": "web_search"}] – läuft über /v1/conversations.
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
        Mistral = _import_mistral()

        client = Mistral(api_key=_api_key())

        # System-Prompt als erste Nachricht einfügen (Mistral-Format).
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        kwargs: dict = {"model": model, "messages": msgs, "max_tokens": max_tokens}
        if temperature is not None:
            kwargs["temperature"] = temperature

        resp = client.chat.complete(**kwargs)

        text = (getattr(resp.choices[0].message, "content", "") or "").strip()
        return text, []

    # ------------------------------------------------------------------
    # Agents API mit Web-Suche (/v1/conversations)
    # ------------------------------------------------------------------

    def _chat_with_web_search(self, model: str, messages: list[dict],
                              system: str, max_tokens: int,
                              temperature: float | None) -> tuple[str, list[str]]:
        """Web-Suche über die Mistral Agents API.

        Flow:
          1. Agent mit web_search-Tool erstellen
          2. client.agents.complete(...) aufrufen
          3. Agent wieder löschen (Cleanup)

        Falls der WebSearchTool-Connector nicht aktiviert ist (HTTP 400,
        code 1800), fällt automatisch auf Standard-Chat zurück – die
        Pipeline bleibt funktionsfähig, nur ohne frische Web-Quellen.
        """
        Mistral = _import_mistral()

        client = Mistral(api_key=_api_key())
        agent_id: str | None = None

        try:
            # 1) Agent mit Web-Suche-Tool anlegen
            agent_kwargs: dict = {
                "model": model,
                "name": "Blog Researcher",
                "description": "Agent for blog research with web search capability.",
                "tools": [{"type": "web_search"}],
            }
            if system:
                agent_kwargs["instructions"] = system
            completion_args: dict = {"max_tokens": max_tokens}
            if temperature is not None:
                completion_args["temperature"] = temperature
            else:
                completion_args["temperature"] = 0.3
            completion_args["top_p"] = 0.95
            agent_kwargs["completion_args"] = completion_args

            agent = client.beta.agents.create(**agent_kwargs)
            agent_id = agent.id

            # 2) Completion aufrufen
            resp = client.agents.complete(
                agent_id=agent_id,
                messages=messages,
            )

            # 3) Antwort extrahieren
            text = (getattr(resp.choices[0].message, "content", "") or "").strip()

            # Quellen-URLs aus dem Text ziehen (Mistral zitiert URLs im Antworttext)
            sources = _extract_urls(text)

            return text, sources

        except Exception as e:
            # WebSearchTool-Connector nicht aktiviert (HTTP 400, code 1800) oder
            # sonstige Agents-API-Fehler → graceful Fallback auf Standard-Chat.
            err_body = str(e)
            import sys
            # Detaillierte Fehlerdiagnose loggen
            detail_parts = [f"  \u26a0 Mistral Agents-API-Fehler: {type(e).__name__}"]
            if hasattr(e, "body"):
                detail_parts.append(f"    API-Body: {e.body}")
            if hasattr(e, "status_code"):
                detail_parts.append(f"    HTTP-Status: {e.status_code}")
            detail_parts.append(f"    Detail: {err_body[:300]}")
            
            if "WebSearchTool" in err_body or "1800" in err_body or "not supported" in err_body:
                detail_parts.append(
                    "    \u2192 WebSearchTool-Connector ist f\u00fcr dieses Konto NICHT aktiviert.\n"
                    "    \u2192 Aktivierung: https://console.mistral.ai \u2192 Connectors \u2192 WebSearchTool \u2192 Enable\n"
                    "    \u2192 Fallback auf Standard-Chat (ohne Web-Suche) \u2013 Pipeline f\u00e4hrt fort."
                )
            else:
                detail_parts.append(
                    "    \u2192 Fallback auf Standard-Chat (ohne Web-Suche) \u2013 Pipeline f\u00e4hrt fort."
                )
            print("\n".join(detail_parts), file=sys.stderr)
            return self._chat_standard(model, messages, system, max_tokens, temperature)

        finally:
            # 4) Agent aufräumen (wichtig: sonst sammeln sich Agents auf dem Konto)
            if agent_id:
                try:
                    client.beta.agents.delete(agent_id)
                except Exception:
                    pass  # Cleanup darf nicht den Hauptpfad brechen

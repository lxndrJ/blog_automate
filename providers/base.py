# providers/base.py – gemeinsame Schnittstelle aller LLM-Provider.
#
# Jeder Adapter (Anthropic, Mistral, Ollama) implementiert:
#   - name:         eindeutiger Provider-Name (für Routing/Logs)
#   - is_available(): True, wenn der Provider genutzt werden KANN
#                     (Key vorhanden, SDK importierbar, Server erreichbar …)
#   - resolve_model(): mappt den in config.py stehenden Modellnamen auf
#                     einen gültigen Modellnamen DES PROVIDERS.
#   - chat():        identische Signatur über alle Provider.
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Gemeinsame Basis für alle LLM-Provider."""

    #: eindeutiger Name, z. B. "anthropic", "mistral", "ollama"
    name: str = "base"

    def is_available(self) -> bool:
        """Standard: verfügbar, solange nichts dagegen spricht.

        Provider ohne Vorbedingung (z. B. Ollama ohne Key) können das
        überschreiben, um z. B. Server-Erreichbarkeit zu prüfen.
        """
        return True

    def resolve_model(self, model: str) -> str:
        """Modellname des Aufrufers in einen Provider-gültigen Namen übersetzen.

        Standard: 1:1 übernehmen.
        """
        return model

    @abstractmethod
    def chat(self,
             model: str,
             messages: list[dict],
             system: str = "",
             max_tokens: int = 4096,
             temperature: float | None = None,
             web_search: bool = False) -> tuple[str, list[str]]:
        """LLM-Call.

        Args:
            model:        (aufruferseitiger) Modellname
            messages:     [{"role": "user", "content": "..."}, ...]
            system:       System-Prompt (optional)
            max_tokens:   max. Antwort-Länge
            temperature:  Sampling-Temperatur (None = Provider-Default)
            web_search:   serverseitige Web-Suche aktivieren (falls unterstützt)

        Returns:
            (text, sources) – sources = Liste von URLs (leer, wenn keine)
        """
        raise NotImplementedError

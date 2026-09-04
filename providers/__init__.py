# providers/ – isolierte LLM-Provider-Adapter.
#
# Jeder Provider implementiert die gemeinsame Signatur aus base.py.
# Agenten sprechen NIE direkt mit einem Provider, sondern immer über
# llm_client.chat() → router → Provider. So bricht ein defekter Provider
# (fehlende SDK, API-Fehler, fehlender Key) nicht die anderen.

# topics.py – kuratierte Themen-Hooks + Duplikat-Prüfung
# Statt „random Land × random Thema" aus der DB: konkrete, kurierbare Briefings.
import json
import os
import random
from datetime import datetime

from config import HISTORY_FILE

# Kuratierte Themen-Briefings. Jedes Element:
#   topic    – prägnanter Hook (wird auch als Arbeitstitel-Vorlage genutzt)
#   context  – was der Artikel konkret behandeln soll (Leitplanken)
TOPICS = [
    {
        "topic": "Ein Tag im Leben: Markttag in einer mittelgroßen Stadt",
        "context": "Wähle eine real existierende Stadt (Europa oder Nahost), beschreibe den Markttag so konkret wie möglich: Gerüche, Preise, Gespräche, ein Gerüst für ein typisches Frühstück. Keine touristischen Top-10-Zwängen.",
    },
    {
        "topic": "Warum wir über {land} fast nur die falschen Dinge wissen",
        "context": "Nimm ein konkretes Land und zerlege 2–3 verbreitete Klischees mit belegten Gegenbeispielen. Schluss mit einer eigenen, uneingeschränkten Einschätzung.",
    },
    {
        "topic": "Eine Speise, die es bei uns nicht gibt – und warum",
        "context": "Wähle ein konkretes Gericht (Name, Region, Stadt) und erkläre seine Geschichte, Zubereitung und warum es in deutsche Küchen kaum einzieht. Echte Namen und Quellen verwenden.",
    },
    {
        "topic": "Der unscheinbare Ort, an dem man landen sollte",
        "context": "Ein konkreter, unglamouröser Ort (kleiner Flughafen, abgelegen Bahnhof, Vorstadt) – warum lohnt sich er statt der Metropole? Konkrete Wege, Preise, Zeitfenster.",
    },
    {
        "topic": "Was {stadt} nachts wirklich ist",
        "context": "Eine reale Stadt (max. 2 Mio. Einwohner), ihre Nachtszene außerhalb der Bars: Spätkauf, Parks, Arbeitsschichten, Nachbarschaft. Ohne Krimi-Ton.",
    },
    {
        "topic": "Fünf Dinge, die mir in {land} niemand vorher gesagt hat",
        "context": "Erste-Person-Perspektive, konkrete Erlebnisse als Rahmen, belegte Details aus der Recherche. Keine erfundenen Personen – Erfahrungen dürfen allgemein bleiben ('ein Händler', 'eine Kollegin').",
    },
    {
        "topic": "Ein historischer Konflikt, der heute still nachwirkt",
        "context": "Wähle ein belegtes historisches Ereignis (max. 30 Jahre alt), erkläre seine leisen Folgen im Alltag einer Stadt oder Region. Ruhiger, journalistischer Ton.",
    },
    {
        "topic": "Transport: von A nach B in {region} – realistisch",
        "context": "Eine konkrete Route (zwei reale Orte). Dauer, Preise, Umstiege, was kaputt gehen kann. Nutzt reale Fahrplan-Infos aus der Recherche.",
    },
    {
        "topic": "Ein Beruf, den man bei uns so nicht kennt",
        "context": "Wähle einen regionalen Beruf (Name, Ort, Auszubildende), wie er heute aussieht und warum es ihn hier nicht gibt. Konkrete Ausbildung, Einkommen, Alltag.",
    },
    {
        "topic": "Sprachliches: Was heißt dieses eine Wort in {stadt}? ",
        "context": "Ein konkretes Orts- oder Fachwort, seine Herkunft, wie es heute klingt, wer es noch verwendet. Etymologie nur wenn belegt.",
    },
]


def pick_topic(used_topics: list[str]) -> dict:
    """Wählt ein kuratiertes Thema, das noch nicht verwendet wurde."""
    remaining = [t for t in TOPICS if t["topic"] not in used_topics]
    if not remaining:
        # Alle mal verwendet → reset (neuer Zyklus)
        remaining = TOPICS
    return random.choice(remaining)


# --- Duplikat-Historie ---------------------------------------------------------
def load_history() -> list[dict]:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_history(history: list[dict]) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-200:], f, ensure_ascii=False, indent=2)


def record(topic: str, filename: str, sources: list[str]) -> None:
    history = load_history()
    history.append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "file": filename,
        "n_sources": len(sources),
    })
    save_history(history)


def used_topics() -> list[str]:
    return [h.get("topic", "") for h in load_history()]

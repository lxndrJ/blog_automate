# topics.py – kuratierte Themen mit konkreten Platzhalter-Auflösungen
# pick_topic() füllt alle Templates mit echten Werten – die LLMs sehen
# nie mehr ein leeres "{region}" und können keine Fragen zurückgeben.
import json
import os
import random
import re
from datetime import datetime

from config import HISTORY_FILE

TOPICS = [
    {
        "topic": "Ein Tag im Leben: Markttag in {stadt}",
        "candidates": ["Leipzig", "Klagenfurt", "Thessaloniki", "Ponta Delgada", "Kosice", "Brest"],
        "context": "Beschreibe den Markttag in dieser Stadt so konkret wie möglich: Standreihen, Gerüche, Preise in Lokalwährung, ein typisches Frühstück am Markt. Keine Top-10-Tonalität.",
    },
    {
        "topic": "Warum wir über {land} fast nur die falschen Dinge wissen",
        "candidates": ["Litauen", "Aserbaidschan", "Nordmazedonien", "Georgien", "Tansania", "Uruguay"],
        "context": "Zerlege 2–3 verbreitete Klischees über dieses Land mit belegten Gegenbeispielen aus der Recherche. Schluss mit einer eigenen, uneingeschränkten Einschätzung.",
    },
    {
        "topic": "Eine Speise, die es bei uns nicht gibt – und warum",
        "candidates": ["Moussaka (Griechenland)", "Karepy (Estland)", "Sfouf (Marokko)", "Pareiko (Italien)"],
        "context": "Erkläre dieses Gericht: Geschichte, Zubereitung, regionale Varianten, warum es in deutsche Küchen kaum einzieht. Echte Namen und Quellen aus der Recherche verwenden.",
    },
    {
        "topic": "Der unscheinbare Ort, an dem man landen sollte",
        "candidates": ["Aalborg (Flughafen), Dänemark", "Lamezia Terme, Italien", "Bergen, Norwegen", "Split, Kroatien"],
        "context": "Warum lohnt sich dieser abgelegen Ort statt der Metropole? Konkrete Wege, Preise, Zeitfenster aus der Recherche.",
    },
    {
        "topic": "Was {stadt} nachts wirklich ist",
        "candidates": ["Marseille", "Wien (jenseits der Innenstadt)", "Tallinn", "Valletta", "Gdańsk"],
        "context": "Die Nachtszene außerhalb der Bars: Spätkauf, Parks, Arbeitsschichten, Nachbarschaft. Ohne Krimi-Ton, mit konkreten Beobachtungen aus der Recherche.",
    },
    {
        "topic": "Fünf Dinge, die mir in {land} niemand vorher gesagt hat",
        "candidates": ["Portugal (Alentejo)", "Schweden (Götaland)", "Türkei (Ägäis-Küste)"],
        "context": "Erste-Person-Perspektive, konkrete Erlebnisse als Rahmen, belegte Details aus der Recherche. Keine erfundenen Personen – Erfahrungen dürfen allgemein bleiben ('ein Händler', 'eine Kollegin').",
    },
    {
        "topic": "Ein historischer Konflikt, der heute still nachwirkt",
        "candidates": [
            "Die Spaltung Zyperns (ab 1974)",
            "Die Balkankriege (1990er) im Alltag kroatischer Städte",
            "Die Entkolonialisierung und ihre Spuren in westafrikanischen Hafenstädten",
        ],
        "context": "Erkläre die leisen Folgen dieses Ereignisses im Alltag einer konkreten Stadt oder Region. Ruhiger, journalistischer Ton, belegt aus der Recherche.",
    },
    {
        "topic": "{route} – die ehrliche Fahrzeit",
        "candidates": [
            "Wien–Prag mit dem Bus",
            "Lissabon–Porto mit der Bahn",
            "Hanoi–Huế per Bus",
            "Athen–Ioannina per Bus",
            "Warschau–Lwiw über die Grenze",
        ],
        "context": "Eine konkrete Route. Reale Dauer, Preise, Umstiege, was häufig schiefgeht. Nur Fahrplan-/Preis-Infos aus der Recherche verwenden, keine Vermutungen.",
    },
    {
        "topic": "Ein Beruf, den man bei uns so nicht kennt",
        "candidates": [
            "Fischräucherei-Inhaber an der deutschen Nordseeküste",
            "Eselsführer in griechischen Bergdörfern",
            "Seifenmacher in Marseille",
        ],
        "context": "Wie sieht dieser regionale Beruf heute aus? Konkrete Ausbildung, Einkommen, Alltag – belegt aus der Recherche. Warum existiert er in Deutschland so nicht.",
    },
    {
        "topic": "Sprachlich: Wie heißt dieses eine Wort in {stadt} wirklich?",
        "candidates": ["Wien (Schmäh vs. Hochdeutsch)", "Hamburg (Schiffersprache im Alltag)", "Rom (Dialektwörter in der Innenstadt)", "Kairo (viertelspezifische Arabismen)"],
        "context": "Ein konkretes Orts-/Fachwort, seine Herkunft, wie es heute klingt, wer es noch verwendet. Etymologie nur wenn belegt.",
    },
]


def pick_topic(used_topics: list[str]) -> dict:
    """Wählt ein kuratiertes Thema und füllt alle Platzhalter konkret aus.

    Rückgabe: {"topic": <befüllt>, "context": <befüllt>, "base": <Template>}
    "base" dient der Duplikat-Erkennung über Zyklen hinweg.
    """
    remaining = [t for t in TOPICS if t["topic"] not in used_topics]
    if not remaining:
        remaining = TOPICS
    t = random.choice(remaining)
    concrete = random.choice(t.get("candidates", [""]))

    if "{route}" in t["topic"]:
        suffix = t["topic"].split("{route}", 1)[1].strip().lstrip("–- ").strip() or ""
        filled_topic = f"{concrete} – {suffix}" if suffix else concrete
        filled_context = "Konkretes Beispiel: %s. " % concrete + t["context"]
    else:
        filled_topic = t["topic"]
        for key in re.findall(r"\{(\w+)\}", t["topic"]):
            filled_topic = filled_topic.replace("{%s}" % key, concrete)
        filled_context = t["context"]
        for key in re.findall(r"\{(\w+)\}", t["context"]):
            filled_context = filled_context.replace("{%s}" % key, concrete)
        # Kandidaten-Name immer explizit in den Kontext – auch wenn das
        # Thema keinen Platzhalter hat (z. B. "Eine Speise …").
        if concrete and concrete not in filled_context:
            filled_context = "Konkretes Beispiel: %s. " % concrete + filled_context

    return {"topic": filled_topic, "context": filled_context, "base": t["topic"]}


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


def record(topic: str, base: str, filename: str, sources: list[str]) -> None:
    history = load_history()
    history.append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "base": base,
        "file": filename,
        "n_sources": len(sources),
    })
    save_history(history)


def used_topics() -> list[str]:
    return [h.get("base", h.get("topic", "")) for h in load_history()]

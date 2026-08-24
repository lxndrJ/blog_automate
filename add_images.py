#!/usr/bin/env python3
"""add_images.py – Bilde jedes Blog-Post mit 2 thematisch passenden Bildern aus.

Strategie
  • Leitthema  → aus dem Post-Titel        → Bild OBEN (vor der H1)
  • Nebenthema → aus den ##-Abschnitten    → Bild UNTEN (vor den Quellen)

Die Suchbegriffe werden aus dem INHALT abgeleitet (nicht nur Titel):
  1. Ort/Land erkennen (bekannte Namen + Großbuchstaben-Wörter)
  2. Deutsches Thema → Englisch übersetzen (THEME_EN)
  3. Query = Ort + bis zu 2 Themenwörter
Jeder Schritt wird als Debug-Output ausgegeben, damit man genau sieht,
wie der Suchbegriff entstanden ist.

Suche: Unsplash (Primär, schnelles CDN) → Wikimedia Commons (Fallback).

Verwendung
    python add_images.py                 # alle Posts im eigenen _posts/
    python add_images.py --dry-run       # nur anzeigen, nichts schreiben
    python add_images.py --file <name>   # nur ein bestimmtes Post (Teilstring)
    python add_images.py --limit N       # nur die ersten N Posts
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from image import pick_image

# ------------------------------------------------------------------- Argumente
args = sys.argv[1:]
DRY_RUN = "--dry-run" in args
FILE_FILTER = None
LIMIT = None
if "--file" in args:
    FILE_FILTER = args[args.index("--file") + 1]
if "--limit" in args:
    LIMIT = int(args[args.index("--limit") + 1])

POSTS_DIR = Path(__file__).resolve().parent / "_posts"

# ------------------------------------------------------------------- DE → EN
# Themenwörter aus dem Blog-Vokabular → englische Suchbegriffe.
# Reihenfolge im Dictionary ist egal – beim Abgleich sortiere ich nach Länge
# (längere Treffer zuerst), damit z. B. "nachtleben" vor "nachts" gewinnt.
THEME_EN = {
    # Nachleben / Stadt
    "nachtleben": "nightlife", "nachts": "night", "nachtclub": "nightclub",
    "bar": "bar", "kneipe": "pub", "kino": "cinema", "filmfestival": "film festival",
    # Essen & Trinken
    "kulinarische": "food", "küche": "food", "rezepte": "recipes",
    "speise": "food", "speisen": "food", "gericht": "dishes", "gerichte": "dishes",
    "rezept": "recipes", "süßspeisen": "dessert", "süßspeise": "dessert",
    "backtraditionen": "baking", "fischgerichte": "fish", "fisch": "fish",
    "getränke": "drinks", "braukunst": "brewing", "bier": "beer",
    "wein": "wine", "kaffee": "coffee", "street food": "street food",
    "bratwurst": "grill", "braten": "roast", "brat": "roast",
    "räuchern": "smoked", "räucherer": "smoked", "räucher": "smoked",
    "vegetarische": "vegetarian", "saisonale": "seasonal", "spezialitäten": "specialty",
    # Natur / Umwelt
    "natur": "nature", "flora": "flora", "fauna": "wildlife",
    "wildlife": "wildlife", "wanderwege": "hiking trail", "wandern": "hiking",
    "geologie": "geology", "geologische": "geology", "vulkan": "volcano",
    "schutzgebiete": "protected area", "nationalparks": "national park",
    "nationalpark": "national park", "wälder": "forest", "wald": "forest",
    "forstwirtschaft": "forestry", "landwirtschaft": "agriculture",
    "klimazonen": "climate", "klima": "climate", "küste": "coast",
    "küstenlandschaften": "coastline", "insel": "island", "berge": "mountains",
    "gebirge": "mountains", "wüste": "desert", "süßwasser": "wetland",
    # Transport / Technik
    "transport": "transport", "verkehr": "transport", "mobilität": "transport",
    "fahrzeuge": "vehicles", "flugzeug": "airplane", "schiff": "ship",
    "zukunftstechnologien": "technology", "digital": "digital",
    "industrialisierung": "industrial", "energie": "energy",
    "energiequellen": "energy",
    # Kultur / Kunst
    "kultur": "culture", "kulturelle": "culture", "musik": "music",
    "komponisten": "composer", "musiker": "musician", "theater": "theater",
    "oper": "opera", "literatur": "literature", "literaturgeschichte": "literature",
    "museen": "museum", "museum": "museum", "gedenkstätten": "memorial",
    "archäologische": "archaeology", "funde": "excavation",
    "handwerk": "craft", "handwerkskunst": "craft", "tradition": "traditional",
    "trachten": "traditional costume", "bräuche": "customs",
    "hochzeitsbräuche": "wedding", "rituale": "rituals", "religiöse": "religious",
    "märchen": "folklore", "sagen": "legends", "symbolik": "symbolism",
    "feste": "festival", "feiertage": "festivals",
    # Sprache
    "sprache": "language", "dialekte": "language", "sprachvielfalt": "languages",
    "wort": "language",
    # Geschichte
    "geschichte": "history", "zeitgeschichte": "history",
    "kolonialgeschichte": "colonial history", "mittelalterliche": "medieval",
    "kriege": "war", "konflikte": "conflict", "entdecker": "explorer",
    "reisende": "travelers",
    # Gesellschaft / Politik
    "politik": "politics", "politiker": "politician", "wissenschaftler": "scientist",
    "wissenschaft": "science", "forschung": "research",
    "forschungseinrichtungen": "research institute", "bildung": "education",
    "migration": "migration", "diaspora": "diaspora", "sicherheit": "safety",
    # Wirtschaft
    "wirtschaft": "economy", "wirtschaftspolitik": "economy",
    "arbeitsmarkt": "jobs", "arbeitsmarkttrends": "jobs", "finanzwesen": "finance",
    "start-ups": "startup", "gründerkultur": "startup", "exportprodukte": "export",
    "export": "export", "nachhaltige": "sustainable", "unternehmen": "business",
    # Reisen
    "budgetreisen": "budget travel", "backpacking": "backpacking",
    "reiseführer": "travel", "geheimtipps": "hidden gems",
    "städtereisen": "city trip", "familie": "family", "wellness": "wellness",
    "erholung": "leisure", "unterkunft": "accommodation", "unterkunftsarten": "accommodation",
    "fotografie": "photography", "naturfotografie": "nature photography",
    "astronomie": "astronomy", "sternenhimmel": "starry sky",
    "städt": "city", "stadt": "city", "viertel": "district",
}
# Nach Länge sortiert (längere zuerst) für sauberes Ersetzen.
THEME_EN = dict(sorted(THEME_EN.items(), key=lambda kv: len(kv[0]), reverse=True))

# Generische ##-Überschriften → taugen NICHT als Nebenthema-Bild.
GENERIC_HEADINGS = [
    "fazit", "quellen", "ausblick", "einblick", "blick nach vorne",
    "zukunftsperspektiven", "zukunft", "praktische tipps", "praktische reisetipps",
    "praktisch", "warum das", "persönlich", "mein fazit", "herausforderungen und chancen",
    "moderne perspektiven", "moderne interpretationen", "moderne herausforderungen",
    "kulturelle resonanzen", "resilienz", "wurzeln der gemeinschaft",
    "warum das alles wichtig ist", "warum das wichtig ist", "kurzfazit",
    "zusammenfassung", "einführung", "vorwort", "nachwort", "einleitung",
    "kulturelle bedeutung", "kulturelle dimension", "die kulturelle",
]

# ------------------------------------------------------------------- Ort/Land
KNOWN_LOCATIONS = [
    "Antarktis", "Jemen", "Sambia", "Niue", "Heard", "Gabun", "Kiribati",
    "Tokelau", "Weissrussland", "Belarus", "weißrussland", "Tadschikistan", "Äthiopien",
    "Wallis", "Futuna", "Zentralafrikanische", "Jungferninseln", "Saudi",
    "Mikronesien", "Lettland", "Amerikanische", "Botswana", "Algerien",
    "Kenia", "Niger", "Togo", "Armenien", "Tunesien", "Sudan", "Saint",
    "Barthélemy", "Aruba", "Libanon", "Macao", "Norfolkinsel", "Curaçao",
    "Mayotte", "Vukovar", "Kroatien", "Tschechien", "Tschad", "Fiji",
    "Vanuatu", "Mongolei", "Brasilien", "Kongo", "Georgien", "Trinidad",
    "Tobago", "Elfenbeinküste", "Sint Maarten", "Seychellen", "Kap Verde",
    "Komoren", "Marokko", "Ägypten", "Libyen", "Mali",
    "Zambia", "Malawi", "Mosambik", "Madagaskar", "Mauritius", "Lesotho",
    "Eswatini", "Simbabwe", "Namibia", "Angola", "Polynesien", "Neukaledonien",
    "Tonga", "Samoa", "Kiribati", "Tuvalu", "Palau", "Marshall",
    "Nauru", "Cookinseln", "Melanesien", "Griechenland", "Slowakei",
    "Schweden", "Schweiz", "Deutschland", "Estland", "Benin", "Brunei",
    "Dominica", "Kasachstan", "Kleinere", "Turks", "Caicosinseln",
    "Wallis", "Futuna", "Götaland", "Åland", "Åland", "Färschen",
    "Tallinn", "Lasnamäe", "Noblessner", "Kadriorg", "Oranjestad", "Moroni",
    "Tallinn", "Vormski", "PÖFF", "Cacco", "Valletta", "Thessaloniki",
]
KNOWN_LOCATIONS = sorted(set(KNOWN_LOCATIONS), key=len, reverse=True)

# Deutsche Füll-/Artikelwörter (für die Query-Feinreinigung).
STOP = {"der", "die", "das", "und", "den", "dem", "ein", "eine", "einer",
        "einem", "einen", "eines", "in", "im", "auf", "bei", "von", "zu",
        "mit", "für", "um", "als", "oder", "aber", "nicht", "auch", "wie",
        "während", "zwischen", "nach", "vor", "an", "am", "aus", "über",
        "unter", "ohne", "sich", "was", "wer", "welche", "dass", "wenn"}


def extract_location(topic: str) -> str | None:
    """Erkennt einen konkreten Ort/Landnamen im Text (für die Such-Query).

    Wichtig: nur Namen aus der KNOWN_LOCATIONS-Liste. Eine generische
    Großbuchstaben-Heuristik würde Zufalls-Eigennamen (PÖFF, Bolt, Noblessner-Brands …)
    als „Ort" durchlassen und die Such-Query vergiften.
    """
    low = topic.lower()
    for loc in KNOWN_LOCATIONS:
        if loc.lower() in low:
            return loc
    return None


def translate_theme(topic: str) -> list[str]:
    """Liefert die englischen Themenwörter (aus THEME_EN), die im Text vorkommen.

    Funktioniert auch bei zusammengesetzten Wörtern (Fischräucherer → smoked, fish)
    und bei Großbuchstaben (Das Gericht → dishes).
    """
    low = topic.lower()
    found = []
    for de, en in THEME_EN.items():
        # Teilstring-Matching (nicht nur Wortgrenzen) → trifft auch Komposita
        if de in low and en not in found:
            found.append(en)
        if len(found) >= 3:
            break
    return found


def build_query(topic: str) -> tuple[str, str, str]:
    """Baut eine englische Unsplash-Query aus einem deutschen Thema.

    Rückgabe: (query, ort, themen_de) – letztere beiden für den Debug-Output.
    """
    ort = extract_location(topic)
    themen_en = translate_theme(topic)

    parts: list[str] = []
    if ort:
        parts.append(ort)
    for t in themen_en[:2]:
        if t not in parts:
            parts.append(t)

    # Fallback: wenn weder Ort noch Thema übersetzt wurde → wichtigste Inhalte-Wörter
    if not parts:
        words = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", topic)
                 if len(w) > 3 and w.lower() not in STOP][:3]
        parts = words

    query = " ".join(parts) if parts else topic
    return query, ort or "(kein Ort)", ", ".join(themen_en) or "(kein DE→EN-Treffer)"


# ------------------------------------------------------------------- Themen
def parse_front_matter(text: str) -> tuple[list[str], str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def get_title(fm_lines: list[str]) -> str:
    for l in fm_lines:
        if l.strip().startswith("title:"):
            return l.split(":", 1)[1].strip().strip('"')
    return ""


def get_headings(body: str) -> list[str]:
    return [h.strip() for h in re.findall(r"^##\s+(.+)$", body, re.MULTILINE)]


def is_generic(heading: str) -> bool:
    low = heading.lower()
    return any(g in low for g in GENERIC_HEADINGS)


def score_heading(h: str) -> int:
    """Wie gut taugt eine ##-Überschrift als Nebenthema-Bild?"""
    s = 0
    low = h.lower()
    if extract_location(h):
        s += 3                       # konkreter Ort → starke Bildsuche
    if translate_theme(h):
        s += 2                       # bekanntes Thema → gute Übersetzung
    if ":" in h:
        s += 1                       # "Titel: Untertitel" → oft spezifisch
    if len(h) < 8:
        s -= 3                       # zu kurz → zu generisch
    if is_generic(h):
        s -= 100                     # hart ausschließen
    return s


def pick_subtheme(title: str, headings: list[str]) -> str | None:
    """Wählt die beste ##-Überschrift als Nebenthema (≠ Titel)."""
    title_low = title.lower()
    candidates = [h for h in headings if not is_generic(h) and h.lower() != title_low]
    if not candidates:
        return None
    return max(candidates, key=score_heading)


# ------------------------------------------------------------------- Einbau
def strip_images(body: str) -> str:
    """Entfernt alle bestehenden Markdown-Bild-Embeds (idempotent)."""
    return re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)


def insert_top_image(body: str, alt: str, url: str, attribution: str = "") -> str:
    """Fügt das Leitthema-Bild ganz oben ein (vor der H1, sonst am Anfang).
    
    Attribution (Unsplash-Foto) wird als HTML-Kommentar hinzugefügt.
    """
    embed = f"![{alt}]({url})"
    if attribution:
        embed = f"<!-- {attribution} -->\n" + embed
    m = re.search(r"^#\s", body, re.MULTILINE)
    if m:
        pos = m.start()
        return body[:pos] + embed + "\n\n" + body[pos:]
    return embed + "\n\n" + body.lstrip("\n")


def insert_bottom_image(body: str, alt: str, url: str, attribution: str = "") -> str:
    """Fügt das Nebenthema-Bild unten ein (vor '## Quellen', sonst vor letztem '---').
    
    Attribution (Unsplash-Foto) wird als HTML-Kommentar hinzugefügt.
    """
    embed = f"![{alt}]({url})"
    if attribution:
        embed = f"<!-- {attribution} -->\n" + embed
    m = re.search(r"^##\s+Quellen", body, re.MULTILINE)
    if m:
        pos = m.start()
        return body[:pos].rstrip("\n") + "\n\n" + embed + "\n\n" + body[pos:]
    # Vor dem letzten Trenner (Footer)
    idx = body.rfind("\n---")
    if idx != -1:
        return body[:idx].rstrip("\n") + "\n\n" + embed + "\n" + body[idx:]
    return body.rstrip("\n") + "\n\n" + embed + "\n"


# ------------------------------------------------------------------- Bildsuche
from image import commons_pick, unsplash_search

UNSPLASH_BUDGET = 30        # max. Unsplash-Calls pro Durchlauf (Limit: 50/h)
UNSPLASH_USED = [0]         # Counter über die ganze Laufzeit
UNSPLASH_RATE_LIMITED = [False]  # True → Unsplash komplett abschalten


def find_image(topic: str, query: str) -> dict | None:
    """Unsplash zuerst (bessere Fotos, schnelles CDN), Wikimedia als Fallback.

    Schaltet Unsplash ab, sobald das Budget aufgebraucht ODER ein 403
    (Rate-Limit) erkannt wurde – sonst würde jeder weitere Versuch
    ~15 s an Retries/Backoff verschwendet.
    """
    # 1. Unsplash (Primär) – nur solange Budget da ist und kein 403 kam
    if UNSPLASH_USED[0] < UNSPLASH_BUDGET and not UNSPLASH_RATE_LIMITED[0]:
        img = unsplash_search(query, "landscape")
        if img and img.get("url"):
            UNSPLASH_USED[0] += 1
            return img
        # 403 / Rate-Limit erkannt → für den Rest des Laufs abschalten
        UNSPLASH_RATE_LIMITED[0] = True
    # 2. Wikimedia (Fallback, unbegrenzt)
    img = commons_pick(topic)
    if img and img.get("url"):
        return img
    return None


# ------------------------------------------------------------------- Hauptlauf
def process(f: Path, verbose: bool = True) -> dict:
    text = f.read_text(encoding="utf-8")
    fm, body = parse_front_matter(text)
    title = get_title(fm) or f.stem

    leitthema = title
    nebenthema = pick_subtheme(title, get_headings(body))

    # --- Leitthema (oben) ---
    q_leit, ort_leit, th_leit = build_query(leitthema)
    img_leit = find_image(leitthema, q_leit)
    if not img_leit and ort_leit != "(kein Ort)":
        img_leit = find_image(ort_leit, ort_leit)
        if img_leit:
            q_leit = ort_leit

    # --- Nebenthema (unten) ---
    img_nebe = None
    q_nebe = ort_nebe = th_nebe = None
    if nebenthema:
        q_nebe, ort_nebe, th_nebe = build_query(nebenthema)
        img_nebe = find_image(nebenthema, q_nebe)
        if not img_nebe and ort_nebe != "(kein Ort)":
            img_nebe = find_image(ort_nebe, ort_nebe)
            if img_nebe:
                q_nebe = ort_nebe

    # --- Debug-Output ---
    if verbose:
        print(f"\n→ {f.name}")
        print(f"  [Leitthema]  {leitthema}")
        print(f"      Ort: {ort_leit}   |   DE→EN: {th_leit}")
        print(f"      QUERY: \"{q_leit}\"   →   "
              f"({img_leit['source']}) " if img_leit and img_leit.get('url')
              else f"      QUERY: \"{q_leit}\"   →   ❌ kein Bild")
        if img_leit and img_leit.get("url"):
            print(f"      URL:   {img_leit['url'][:80]}…")
        if nebenthema:
            print(f"  [Nebenthema] {nebenthema}")
            print(f"      Ort: {ort_nebe}   |   DE→EN: {th_nebe}")
            if img_nebe and img_nebe.get("url"):
                print(f"      QUERY: \"{q_nebe}\"   →   ({img_nebe['source']})")
                print(f"      URL:   {img_nebe['url'][:80]}…")
            else:
                print(f"      QUERY: \"{q_nebe}\"   →   ❌ kein Bild")
        else:
            print(f"  [Nebenthema] (keine passende ##-Überschrift gefunden)")

    # --- Einbau (nur wenn mind. ein Bild da ist) ---
    if img_leit and img_leit.get("url"):
        body2 = strip_images(body)
        # Attribution nur bei Unsplash-Bildern
        leit_attr = img_leit.get("attribution", "")
        body2 = insert_top_image(body2, leitthema, img_leit["url"], leit_attr)
        if img_nebe and img_nebe.get("url") and img_nebe["url"] != img_leit["url"]:
            nebe_attr = img_nebe.get("attribution", "")
            body2 = insert_bottom_image(body2, nebenthema, img_nebe["url"], nebe_attr)

        # Frontmatter image: → Leitthema-Bild (Cover/OG)
        new_fm = [l for l in fm if not l.strip().startswith("image:")]
        date_idx = next((i for i, l in enumerate(new_fm) if l.strip().startswith("date:")), 0)
        new_fm.insert(date_idx + 1, f"image: {img_leit['url']}")
        out = "---\n" + "\n".join(new_fm) + "\n---" + body2

        if not DRY_RUN:
            f.write_text(out, encoding="utf-8")
        return {"ok": True, "leit": bool(img_leit.get("url")),
                "nebe": bool(img_nebe and img_nebe.get("url"))}
    return {"ok": False}


def main() -> int:
    if not POSTS_DIR.is_dir():
        print(f"FEHLER: {POSTS_DIR} existiert nicht", file=sys.stderr)
        return 2
    files = sorted(POSTS_DIR.glob("*.md"))
    if FILE_FILTER:
        files = [f for f in files if FILE_FILTER in f.name]
    if LIMIT:
        files = files[:LIMIT]

    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}{len(files)} Posts zu bebildern\n")
    ok = beidre = kein = 0
    for f in files:
        r = process(f)
        time.sleep(2)  # Rate-Limit-Schutz (Unsplash + Wikimedia)
        if not r.get("ok"):
            kein += 1
        elif r.get("leit") and r.get("nebe"):
            beidre += 1
        else:
            ok += 1
    print(f"\nFertig: {beidre} mit 2 Bildern, {ok} mit 1 Bild, {kein} ohne Bild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

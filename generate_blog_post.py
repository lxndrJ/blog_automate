# generate_blog_post.py

import sqlite3
import random
import anthropic
import os
from datetime import datetime
from anthropic_config import MODEL, TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT, generate_prompt
from unsplash_image import search_unsplash_image
from markdown_writer import save_markdown

def get_random_country():
    conn = sqlite3.connect("countries.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name_de, capital FROM countries ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result

def get_random_theme():
    conn = sqlite3.connect("themes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT theme, theme_category FROM themes ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result

# === Schritt 1: Land und Thema auswählen ===
country_name, capital = get_random_country()
theme, category = get_random_theme()

# === Schritt 2: Prompt vorbereiten ===
prompt = generate_prompt(theme, country_name, capital, category)

# === Schritt 3: Anthropic API aufrufen ===
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model=MODEL,
    max_tokens=MAX_TOKENS,
    temperature=TEMPERATURE,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt}]
)

# === Schritt 4: Unsplash Bild suchen ===
image_query = f"{theme} {country_name}"
image_url = search_unsplash_image(image_query)

# === Schritt 5: Markdown speichern ===
markdown_title = f"{theme} in {country_name}"
markdown_content = response.content[0].text
filename = save_markdown(markdown_title, markdown_content, image_url)

# === Schritt 6: Logging ===
with open("blog_log.txt", "a", encoding="utf-8") as log:
    log.write(f"---\n")
    log.write(f"Datei: {filename}\n")
    log.write(f"Land: {country_name}, Hauptstadt: {capital}\n")
    log.write(f"Thema: {theme}, Kategorie: {category}\n")
    log.write(f"Prompt:\n{prompt}\n")
    log.write(f"Bild-URL: {image_url}\n")
    log.write(f"---\n")

print(f"Blogbeitrag erfolgreich erstellt: {filename}")

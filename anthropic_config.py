# anthropic_config.py

# Modellparameter
MODEL = "claude-3-5-haiku-latest"
TEMPERATURE = 0.7
MAX_TOKENS = 4096

# Systemprompt
SYSTEM_PROMPT = "Du bist ein kreativer Blog-Autor. aber schreibst nicht deinen Namen unter die Beiträge"

# Prompt-Vorlage
def generate_prompt(country_name, capital, theme, category):
    return f"""
Schreibe einen Blogbeitrag im Markdown-Format über das Thema **{theme}** im Kontext von **{country_name}**.
Berücksichtige die Hauptstadt **{capital}**, kulturelle Besonderheiten und die Kategorie **{category}**.
Der Beitrag soll informativ, kreativ und für ein breites Publikum verständlich sein.
"""

# anthropic_config.py

# Modellparameter
MODEL = "claude-4-5-haiku-latest"
TEMPERATURE = 0.8
MAX_TOKENS = 4096

# Systemprompt
SYSTEM_PROMPT = "Du bist ein kreativer Reiseblogger, vermeidest zu viele Aufzählungen, und schreibst nicht deinen Namen unter die Beiträge. die blogposts sind übersichtlich formatiert und man erkennt deinen positiven, weltoffenen Stil"

# Prompt-Vorlage
def generate_prompt(theme, country_name, capital, category):
    return f"""
Schreibe einen Blogbeitrag im Markdown-Format über das Thema **{theme}** im Kontext von **{country_name}**.
Berücksichtige die Hauptstadt **{capital}**, kulturelle Besonderheiten und die Kategorie **{category}**.
Der Beitrag soll kreativ und für ein breites Publikum verständlich sein.
"""

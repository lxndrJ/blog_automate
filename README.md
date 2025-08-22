# blog_automate
AI generierter blog

## Automatisierte Blog-Generierung mit GitHub Actions

Dieses Repository enthält eine GitHub Action, die jeden Morgen um 5:00 Uhr UTC automatisch einen Blogbeitrag generiert.

### Setup

#### 1. GitHub Secrets konfigurieren

Fügen Sie die folgenden Secrets in Ihren GitHub Repository-Einstellungen hinzu:

- `ANTHROPIC_API_KEY`: Ihr API-Schlüssel für Anthropic Claude
- `UNSPLASH_ACCESS_KEY`: Ihr Access Key für die Unsplash API

#### 2. Erforderliche Dateien

Das Repository enthält:
- `generate_blog_post.py` - Hauptskript für die Blog-Generierung
- `requirements.txt` - Python-Abhängigkeiten
- `.github/workflows/generate-blog-post.yml` - GitHub Action Workflow
- `countries.db` und `themes.db` - SQLite-Datenbanken mit Ländern und Themen

#### 3. GitHub Action

Die Action läuft automatisch jeden Tag um 5:00 Uhr UTC und:
1. Installiert Python-Abhängigkeiten
2. Führt das Blog-Generierungsskript aus
3. Committed und pushed die generierten Dateien

### Manuelle Ausführung

Sie können die Action auch manuell über den "Actions" Tab in GitHub ausführen.

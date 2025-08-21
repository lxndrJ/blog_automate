import os
from datetime import datetime

def save_markdown(title, content, image_url):
    os.makedirs("_posts", exist_ok=True)
    date_prefix = datetime.today().strftime("%Y%m%d")
    sanitized_title = title.replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    filename = f"{date_prefix}_{sanitized_title}.md"
    filepath = os.path.join("_posts", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

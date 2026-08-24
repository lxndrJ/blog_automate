from datetime import datetime
import os

def save_markdown(title, content, image_url=None, categories=None):
    # Ensure _posts directory exists
    os.makedirs('_posts', exist_ok=True)

    # Format date and filename for Jekyll
    date_obj = datetime.now()
    date_str = date_obj.strftime("%Y-%m-%d")
    # Include time in ISO 8601 format for proper RSS feed generation
    # Format: YYYY-MM-DD HH:MM:SS +TZINFO
    date_str_with_time = date_obj.strftime("%Y-%m-%d %H:%M:%S %z")
    safe_title = title.replace(" ", "-").replace("**", "").lower()
    filename = f"_posts/{date_str}-{safe_title}.md"

    # Prepare YAML front matter
    front_matter = "---\n"
    front_matter += "layout: post\n"
    front_matter += f"title: \"{title}\"\n"
    # Use date WITH time for proper RSS feed generation
    front_matter += f"date: {date_str_with_time}\n"
    if categories:
        front_matter += f"categories: {categories}\n"
    if image_url:
        front_matter += f"image: {image_url}\n"
    front_matter += "---\n\n"

    # Write to file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter)
        if image_url:
            f.write(f"![{title}]({image_url})\n\n")
        f.write(content)

    return filename

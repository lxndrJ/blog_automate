import requests
import os

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

def search_unsplash_image(query):
    """
    Searches Unsplash for an image matching the query and returns the image URL.
    """
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape",
        "client_id": UNSPLASH_ACCESS_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("results"):
        return data["results"][0]["urls"]["regular"]
    return None

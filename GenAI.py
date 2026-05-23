from google import genai
import json
import requests
from PIL import Image
import io
from urllib.parse import quote
import os
from dotenv import load_dotenv

# Load the secret variables from the .env file
load_dotenv()

# Grab the keys securely from the environment
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
LASTFM_KEY = os.getenv("LASTFM_API_KEY")

# Initialize the clients using the hidden keys
client = genai.Client(api_key=GEMINI_KEY)
LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def fetch_gemini_metadata(mood, genre, era):
    """Sends the user's inputs to Gemini and returns a structured JSON dictionary."""
    prompt = f"""
    Based on this mood, generate a fictional album. 
    Genre: {genre}
    Era: {era}
    Mood/Journal: "{mood}"

    Return ONLY valid JSON with this exact schema:
    {{
      "album_name": "string",
      "artist_name": "string",
      "year": "string",
      "label": "string",
      "mood_description": "string",
      "cover_prompt": "string",
      "lastfm_tags": ["array of 4-6 lowercase Last.fm tag strings"]
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text.strip()

        # Strip markdown fences if Gemini added them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()

        album_data = json.loads(text)
        return album_data

    except Exception as e:
        print(f"Error communicating with Gemini: {e}")
        return None


def fetch_tracks(tags, required_count):
    """Fetches real tracks from Last.fm based on tags, filtering duplicates."""
    all_tracks = []
    seen_urls = set()  # Used to filter duplicates

    for tag in tags:
        # Stop searching if we already have enough tracks
        if len(all_tracks) >= required_count:
            break

        params = {
            "method": "tag.gettoptracks",
            "tag": tag,
            "limit": required_count,
            "api_key": LASTFM_KEY,
            "format": "json"
        }

        try:
            headers = {"User-Agent": "AlbumCoverStudio/1.0"}
            response = requests.get(LASTFM_BASE_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            tracks = data.get("tracks", {}).get("track", [])

            for t in tracks:
                url = t.get("url")
                # Filter duplicates
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_tracks.append({
                        "title": t.get("name"),
                        "artist": t.get("artist", {}).get("name"),
                        "url": url
                    })

                # Check if we have reached the required limit
                if len(all_tracks) >= required_count:
                    break

        except Exception as e:
            print(f"Error fetching tracks for tag '{tag}': {e}")

    return all_tracks[:required_count]


def generate_cover(prompt, genre):
    """Generates an album cover using Pollinations.ai based on the prompt."""
    full_prompt = f"Album cover art, {genre} style. {prompt}"
    encoded = quote(full_prompt)

    url = (f"https://image.pollinations.ai/prompt/{encoded}"
           f"?width=600&height=600&nologo=true")

    try:
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        # Convert downloaded bytes directly into a PIL Image
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"Error generating cover image: {e}")
        return None
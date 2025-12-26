import tweepy
from google import genai
import feedparser
import os
import requests
import re

# --- CONFIGURATION ---
TARGET_RSS_FEED = "https://rss.app/feeds/rlQPF5J5AVC4Vunv.xml"

def get_view_count(entry):
    """Extracts numeric views from the RSS entry description/summary."""
    text = entry.get('summary', '') + entry.get('description', '')
    match = re.search(r'([\d,.]+K?M?)\s*views', text, re.IGNORECASE)
    if not match: return 0
    val_str = match.group(1).upper().replace(',', '')
    try:
        if 'M' in val_str: return float(val_str.replace('M', '')) * 1_000_000
        if 'K' in val_str: return float(val_str.replace('K', '')) * 1_000
        return float(val_str)
    except: return 0

def post_best_tweet():
    try:
        # 1. SETUP APIS
        auth = tweepy.OAuth1UserHandler(os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"), os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
        api_v1 = tweepy.API(auth)
        client_v2 = tweepy.Client(consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"), access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"))
        gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # 2. FETCH AND FILTER NEW POSTS
        print("Fetching RSS feed...", flush=True)
        feed = feedparser.parse(TARGET_RSS_FEED)
        new_entries = []
        history = ""
        if os.path.exists("last_post_id.txt"):
            with open("last_post_id.txt", "r") as f: history = f.read()

        for entry in feed.entries:
            if entry.link not in history:
                entry.view_score = get_view_count(entry)
                new_entries.append(entry)

        if not new_entries:
            print("No new posts found.", flush=True)
            return

        # 3. SELECT THE "BEST" ONE
        best_entry = max(new_entries, key=lambda x: x.view_score)
        print(f"Top post selected ({best_entry.view_score} views): {best_entry.link}", flush=True)

        # 4. DOWNLOAD IMAGE (if exists)
        media_id = None
        img_url = None
        if 'media_content' in best_entry: img_url = best_entry.media_content[0]['url']
        elif 'links' in best_entry:
            for link in best_entry.links:
                if 'image' in link.get('type', ''): img_url = link.href

        if img_url:
            img_resp = requests.get(img_url)
            if img_resp.status_code == 200:
                with open("temp.jpg", "wb") as f: f.write(img_resp.content)
                media = api_v1.media_upload("temp.jpg")
                media_id = media.media_id
                os.remove("temp.jpg")

        # 5. AI REWRITE (Gemini 2.0 Flash Lite)
        tweet_text = best_entry.title[:275]
        try:
            ai_resp = gemini.models.generate_content(model='gemini-2.0-flash-lite', contents=f"Rewrite for fans: {best_entry.title}")
            tweet_text = ai_resp.text.strip()[:275]
        except: print("AI failed, using original title.")

        # 6. POST TO X
        client_v2.create_tweet(text=tweet_text, media_ids=[media_id] if media_id else None)

        # 7. UPDATE MEMORY (Mark ALL discovered entries as seen)
        with open("last_post_id.txt", "a") as f:
            for e in new_entries: f.write(e.link + "\n")
        print("Success!", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    post_best_tweet()

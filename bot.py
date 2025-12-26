import tweepy
from google import genai
import feedparser
import os
import requests
import time
from datetime import datetime, timezone

# --- CONFIGURATION ---
TARGET_RSS_FEED = "https://rss.app/feeds/rlQPF5J5AVC4Vunv.xml"

def post_tweet():
    try:
        # 1. SETUP APIS
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        api_v1 = tweepy.API(auth)
        client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # 2. GET FEED ENTRIES
        print("Fetching RSS feed...", flush=True)
        feed = feedparser.parse(TARGET_RSS_FEED)
        if not feed.entries:
            print("No entries found in feed.", flush=True)
            return

        # Process entries (Oldest to newest)
        for entry in reversed(feed.entries):
            
            # Memory Check (Don't repost same thing)
            if os.path.exists("last_post_id.txt"):
                with open("last_post_id.txt", "r") as f:
                    if entry.link in f.read():
                        continue

            print(f"New post found: {entry.link}", flush=True)

            # 3. IMAGE DETECTION
            media_id = None
            img_url = None
            if 'media_content' in entry:
                img_url = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if 'image' in link.get('type', ''):
                        img_url = link.href

            if img_url:
                print(f"Downloading image: {img_url}", flush=True)
                img_resp = requests.get(img_url)
                if img_resp.status_code == 200:
                    with open("temp.jpg", "wb") as f:
                        f.write(img_resp.content)
                    media = api_v1.media_upload("temp.jpg")
                    media_id = media.media_id
                    os.remove("temp.jpg")

            # 4. AI REWRITE (Using Flash-Lite for high limits)
            print("Requesting AI rewrite...", flush=True)
            prompt = f"Rewrite this update for a fan page. Keep facts/links the same. Max 275 chars: {entry.title}"
            
            tweet_text = ""
            try:
                ai_response = gemini.models.generate_content(
                    model='gemini-2.0-flash-lite', 
                    contents=prompt
                )
                tweet_text = ai_response.text.strip()[:275]
            except Exception as e:
                print(f"AI Error: {e}", flush=True)
                # Fallback: Post original title if AI fails
                tweet_text = entry.title[:275]

            # 5. POST TO X
            print("Posting to X...", flush=True)
            if media_id:
                client_v2.create_tweet(text=tweet_text, media_ids=[media_id])
            else:
                client_v2.create_tweet(text=tweet_text)

            # Update Memory
            with open("last_post_id.txt", "a") as f:
                f.write(entry.link + "\n")
            print(f"Successfully posted: {entry.link}", flush=True)
            
            # Small 5-second gap if multiple posts are processed at once
            time.sleep(5)

    except Exception as e:
        print(f"Global Error: {e}", flush=True)

if __name__ == "__main__":
    post_tweet()

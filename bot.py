import tweepy
from google import genai
try:
    from google.api_core import exceptions
except ImportError:
    # Fallback for certain environments
    from google.rpc import status_pb2 as exceptions 
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
        feed = feedparser.parse(TARGET_RSS_FEED)
        if not feed.entries:
            print("No entries found.")
            return

        for entry in reversed(feed.entries):
            # Memory Check
            if os.path.exists("last_post_id.txt"):
                with open("last_post_id.txt", "r") as f:
                    if entry.link in f.read():
                        continue

            # 3. ENFORCE 3-MINUTE DELAY
            published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            seconds_since_post = (now - published_time).total_seconds()
            
            if seconds_since_post < 180:
                wait_needed = 180 - seconds_since_post
                print(f"Waiting {wait_needed:.0f}s to reach the 3-minute mark...")
                time.sleep(wait_needed)

            # 4. IMAGE DETECTION
            media_id = None
            img_url = None
            if 'media_content' in entry:
                img_url = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if 'image' in link.get('type', ''):
                        img_url = link.href

            if img_url:
                img_resp = requests.get(img_url)
                if img_resp.status_code == 200:
                    with open("temp.jpg", "wb") as f:
                        f.write(img_resp.content)
                    media = api_v1.media_upload("temp.jpg")
                    media_id = media.media_id
                    os.remove("temp.jpg")

            # 5. AI REWRITE (Using Flash-Lite for higher limits)
            prompt = f"Rewrite this update for a fan page. Keep facts/links the same. Max 275 chars: {entry.title}"
            
            tweet_text = ""
            for attempt in range(3):
                try:
                    ai_response = gemini.models.generate_content(
                        model='gemini-2.0-flash-lite', 
                        contents=prompt
                    )
                    tweet_text = ai_response.text.strip()[:275]
                    break 
                except Exception as e:
                    if "429" in str(e) or "ResourceExhausted" in str(e):
                        print(f"Rate limit hit. Waiting 30s (Attempt {attempt+1}/3)...")
                        time.sleep(30)
                    else:
                        print(f"AI Error: {e}")
                        break
            
            if not tweet_text:
                continue

            # 6. POST TO X
            if media_id:
                client_v2.create_tweet(text=tweet_text, media_ids=[media_id])
            else:
                client_v2.create_tweet(text=tweet_text)

            # Update Memory
            with open("last_post_id.txt", "a") as f:
                f.write(entry.link + "\n")
            print(f"Success! Posted: {entry.link}")
            
            # Breathing room
            time.sleep(15)

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    post_tweet()

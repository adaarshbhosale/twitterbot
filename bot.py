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
        feed = feedparser.parse(TARGET_RSS_FEED)
        if not feed.entries:
            print("No entries found.")
            return

        # Process from oldest to newest to ensure chronological order
        for entry in reversed(feed.entries):
            
            # Check Memory (Duplicate Check)
            if os.path.exists("last_post_id.txt"):
                with open("last_post_id.txt", "r") as f:
                    if entry.link in f.read():
                        continue

            # 3. ENFORCE 3-MINUTE DELAY
            # Convert published time to UTC datetime
            published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            seconds_since_post = (now - published_time).total_seconds()
            
            if seconds_since_post < 180:
                wait_time = 180 - seconds_since_post
                print(f"Waiting {wait_needed:.0f}s to reach the 3-minute mark...")
                time.sleep(wait_time)

            # 4. IMAGE DETECTION (RSS.app format)
            media_id = None
            img_url = None
            
            # Check common media tags in RSS.app
            if 'media_content' in entry:
                img_url = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if 'image' in link.get('type', ''):
                        img_url = link.href

            if img_url:
                print(f"Downloading image: {img_url}")
                img_resp = requests.get(img_url)
                if img_resp.status_code == 200:
                    with open("temp.jpg", "wb") as f:
                        f.write(img_resp.content)
                    media = api_v1.media_upload("temp.jpg")
                    media_id = media.media_id
                    os.remove("temp.jpg")

            # 5. AI REWRITE (No monthly limits)
            prompt = f"Rewrite this update for a fan page. Keep all facts and links exactly the same, but change the wording. Max 275 characters: {entry.title}"
            ai_response = gemini.models.generate_content(model='gemini-2.0-flash', contents=prompt)
            tweet_text = ai_response.text.strip()[:275]

            # 6. POST TO X
            if media_id:
                client_v2.create_tweet(text=tweet_text, media_ids=[media_id])
            else:
                client_v2.create_tweet(text=tweet_text)

            # Update Memory
            with open("last_post_id.txt", "a") as f:
                f.write(entry.link + "\n")
            print(f"Success! Posted: {entry.link}")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    post_tweet()

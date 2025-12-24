import tweepy
from google import genai
import feedparser
import os
import requests
import random
from datetime import datetime

FEEDS = [
    "https://rss.app/feeds/JZozOSCPSSRNwBWU.xml",
    "https://rss.app/feeds/DbNVy1zAb9BKCHOR.xml",
    "https://rss.app/feeds/3T2tQIIEbKrC5dBM.xml",
    "https://rss.app/feeds/vin9tnvcQJ1qBRhU.xml",
    "https://rss.app/feeds/eXc8beioBXJg6dsf.xml"
]

def post_tweet():
    try:
        # 1. MONTHLY LIMIT CHECK (500/month)
        current_month = datetime.now().strftime("%Y-%m")
        count_file = "tweet_count.txt"
        count = 0
        if os.path.exists(count_file):
            with open(count_file, "r") as f:
                data = f.read().split(",")
                if len(data) == 2 and data[0] == current_month:
                    count = int(data[1])
        
        if count >= 500:
            print(f"Limit reached ({count}/500) for {current_month}. Stopping.")
            return

        # 2. RANDOM TIMING LOGIC (70% chance to run)
        # This makes the 30-min schedule look unpredictable
        if random.random() > 0.7:
            print("Random skip triggered to keep timing natural.")
            return

        # 3. SETUP APIS
        # We use v1.1 for images and v2 for text
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

        # 4. GET LATEST NEWS
        all_news = []
        for url in FEEDS:
            feed = feedparser.parse(url)
            if feed.entries: all_news.extend(feed.entries)
        
        if not all_news: return
        all_news.sort(key=lambda x: x.get('published_parsed', 0), reverse=True)
        latest = all_news[0]
        
        # Check Memory (Duplicate Check)
        if os.path.exists("last_post_id.txt"):
            with open("last_post_id.txt", "r") as f:
                if f.read().strip() == latest.link:
                    print("News already posted. Skipping.")
                    return

        # 5. IMAGE DETECTION
        media_id = None
        img_url = None
        # Try finding image in common RSS tags
        if 'media_content' in latest: img_url = latest.media_content[0]['url']
        elif 'links' in latest:
            for l in latest.links:
                if 'image' in l.get('type',''): img_url = l.href

        if img_url:
            print(f"Downloading image: {img_url}")
            img_data = requests.get(img_url).content
            with open("temp.jpg", "wb") as f: f.write(img_data)
            media = api_v1.media_upload("temp.jpg")
            media_id = media.media_id

        # 6. AI REWRITE (2025 Model)
        prompt = f"Passionately rewrite this Arsenal update for a fan page. Use British fan slang, emojis, and #AFC. Max 270 chars: {latest.title}"
        response = gemini.models.generate_content(model='gemini-2.5-flash-lite', contents=prompt)
        tweet_text = response.text.strip()[:270]

        # 7. POST & UPDATE MEMORY
        if media_id:
            client_v2.create_tweet(text=tweet_text, media_ids=[media_id])
        else:
            client_v2.create_tweet(text=tweet_text)

        with open("last_post_id.txt", "w") as f: f.write(latest.link)
        with open(count_file, "w") as f: f.write(f"{current_month},{count + 1}")
        
        print(f"Success! Monthly Count: {count + 1}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    post_tweet()

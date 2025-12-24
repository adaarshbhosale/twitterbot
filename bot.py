import tweepy
from google import genai
import feedparser
import os

# 1. Your List of 5 RSS Feeds
FEEDS = [
    "https://rss.app/feeds/JZozOSCPSSRNwBWU.xml",
    "https://rss.app/feeds/DbNVy1zAb9BKCHOR.xml",
    "https://rss.app/feeds/3T2tQIIEbKrC5dBM.xml",
    "https://rss.app/feeds/vin9tnvcQJ1qBRhU.xml",
    "https://rss.app/feeds/eXc8beioBXJg6dsf.xml"
]

def post_tweet():
    try:
        # Setup X and Gemini
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Find the newest tweet across all 5 feeds
        all_entries = []
        for url in FEEDS:
            feed = feedparser.parse(url)
            if feed.entries:
                all_entries.extend(feed.entries)
        
        if not all_entries:
            print("No news found in any feed.")
            return

        # Sort all news by time (newest first)
        all_entries.sort(key=lambda x: x.get('published_parsed', 0), reverse=True)
        latest_item = all_entries[0]
        news_id = latest_item.link # Use the link as a unique ID
        news_text = latest_item.title

        # Check Memory: Don't post the same thing twice
        if os.path.exists("last_post_id.txt"):
            with open("last_post_id.txt", "r") as f:
                if f.read().strip() == news_id:
                    print("Already posted this tweet. Skipping...")
                    return

        # AI Rewrite Logic
        prompt = f"Rewrite this Arsenal update in a high-energy, engaging way for a fan page. Add 1-2 emojis and #AFC. Max 280 chars: {news_text}"
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        
        # Post to X
        tweet_content = response.text.strip()
        client.create_tweet(text=tweet_content[:280])
        
        # Update Memory
        with open("last_post_id.txt", "w") as f:
            f.write(news_id)
            
        print(f"Successfully posted: {tweet_content}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    post_tweet()

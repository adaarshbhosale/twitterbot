import tweepy
from google import genai
import feedparser
import os

def post_tweet():
    try:
        # 1. Setup X (Twitter)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # 2. Setup Gemini (New 2025 SDK)
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # 3. Get Arsenal News
        feed_url = "https://www.newsnow.co.uk/h/Sport/Football/Premier+League/Arsenal/Transfer+News?type=rss"
        feed = feedparser.parse(feed_url)
        
        # SAFETY CHECK: If the news feed is empty, stop here.
        if not feed.entries:
            print("No news found right now. Try again later!")
            return

        news_headline = feed.entries[0].title 

        # 4. AI Rewrite
        prompt = f"Rewrite this Arsenal news as an exciting tweet for fans with emojis: {news_headline}"
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        
        # 5. Post
        client.create_tweet(text=response.text[:280])
        print(f"Successfully posted: {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    post_tweet()

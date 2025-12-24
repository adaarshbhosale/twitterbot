import tweepy
import google.generativeai as genai
import feedparser
import os

# Connect to the secrets you just saved
def post_tweet():
    # Setup X
    client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    
    # Setup Gemini
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Get Arsenal News
    feed = feedparser.parse("https://www.newsnow.co.uk/h/Sport/Football/Premier+League/Arsenal/Transfer+News?type=rss")
    news_headline = feed.entries[0].title 

    # AI Rewrite
    prompt = f"Rewrite this Arsenal news headline as an exciting tweet for fans with emojis. Max 280 chars: {news_headline}"
    response = model.generate_content(prompt)
    
    # Post
    client.create_tweet(text=response.text)
    print("Tweet posted successfully!")

if __name__ == "__main__":
    post_tweet()

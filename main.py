import os
import time
import requests
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# File to store history
HISTORY_FILE = 'posted_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_news_articles():
    news_api_key = os.environ.get('NEWS_API_KEY')
    if not news_api_key: return []

    print("Fetching latest news...")
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        articles = []
        
        # STRATEGY CHANGE: Post only 2 articles per run to keep quota safe
        for item in data.get('articles', [])[:2]: 
            if item['title'] == '[Removed]' or not item['content'] or not item['url']:
                continue
                
            html_content = f"""
            <p><i>Source: {item['source']['name']}</i></p>
            <p>{item['description'] or ''}</p>
            <p>{item['content']}</p>
            <p><a href="{item['url']}" target="_blank">Read the full story here</a></p>
            """
            
            articles.append({
                "title": item['title'],
                "content": html_content,
                "url": item['url']
            })
        return articles
    except Exception as e:
        print(f"❌ Failed to fetch news: {e}")
        return []

def main():
    CLIENT_ID = os.environ.get('CLIENT_ID')
    CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
    REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
    raw_blogger_ids = os.environ.get('BLOGGER_IDS', '')
    BLOGGER_IDS = [b_id.strip() for b_id in raw_blogger_ids.split(',') if b_id.strip()]

    posted_history = load_history()
    
    creds = Credentials(
        token=None, refresh_token=REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    service = build('blogger', 'v3', credentials=creds)

    news_articles = get_news_articles()
    if not news_articles:
        print("No new articles to post.")
        return

    for blog_id in BLOGGER_IDS:
        print(f"\n--- Checking Blog: {blog_id} ---")
        for article in news_articles:
            # UNIQUE ID FOR THIS SPECIFIC BLOG AND ARTICLE
            unique_post_id = f"{blog_id}:{article['url']}"
            
            if unique_post_id in posted_history:
                print(f"Skipping (Already Posted to {blog_id}): {article['title'][:30]}...")
                continue
            
            try:
                service.posts().insert(blogId=blog_id, body={"title": article['title'], "content": article['content']}, isDraft=False).execute()
                print(f"✅ Posted to {blog_id}: {article['title'][:30]}...")
                
                # Save as specific to this blog
                posted_history.append(unique_post_id)
                save_history(posted_history)
                
                # SLEEP: Longer delay to keep Google API happy
                time.sleep(45) 
                
            except HttpError as error:
                print(f"❌ Error: {error}")
                if error.resp.status == 429:
                    print("⚠️ Rate limit hit. Sleeping for 2 minutes...")
                    time.sleep(120) # Longer cooldown if we get blocked
        
        # Add a buffer between blogs to prevent burst errors
        print("Moving to next blog...")
        time.sleep(30) 

    print("\n🎉 All tasks completed safely!")

if __name__ == '__main__':
    main()

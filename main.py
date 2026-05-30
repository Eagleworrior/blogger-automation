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
    if not news_api_key:
        return []

    print("Fetching latest news...")
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get('articles', [])[:5]:
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
                "url": item['url'] # We track the URL to prevent duplicates
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

    # Load history
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
            # DEDUPLICATION CHECK
            if article['url'] in posted_history:
                print(f"Skipping (Already Posted): {article['title']}")
                continue
            
            body = {"title": article['title'], "content": article['content']}
            
            try:
                service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
                print(f"✅ Posted: {article['title']}")
                
                # Add to history and save
                posted_history.append(article['url'])
                save_history(posted_history)
                
                time.sleep(15)
            except HttpError as error:
                print(f"❌ Error: {error}")
                if error.resp.status == 429:
                    time.sleep(60)

if __name__ == '__main__':
    main()

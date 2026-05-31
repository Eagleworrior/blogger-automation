import os
import time
import requests
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

INDEX_FILE = 'blog_index.json'
HISTORY_FILE = 'posted_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_next_blog(blogger_ids):
    # Load which blog we posted to last
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            try:
                data = json.load(f)
                index = data.get('index', 0)
            except:
                index = 0
    else:
        index = 0
    
    # Calculate next index for the NEXT run
    next_index = (index + 1) % len(blogger_ids)
    
    # Save the index for the next run to read
    with open(INDEX_FILE, 'w') as f:
        json.dump({'index': next_index}, f)
        
    return blogger_ids[index]

def get_news_articles():
    news_api_key = os.environ.get('NEWS_API_KEY')
    if not news_api_key: 
        print("❌ No NEWS_API_KEY found.")
        return []

    print("Fetching latest news from News API...")
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        articles = []
        
        # Grab up to 2 articles to keep the script running fast
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

    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BLOGGER_IDS]):
        print("❌ CRITICAL ERROR: Missing one or more environment variables.")
        return

    # 1. Determine which specific blog to target during this 2-hour window
    target_blog = get_next_blog(BLOGGER_IDS)
    print(f"🎯 Target blog for this execution window: {target_blog}")

    # 2. Load posted URLs log
    posted_history = load_history()

    # 3. Authenticate with Google Blogger
    creds = Credentials(
        token=None, refresh_token=REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    service = build('blogger', 'v3', credentials=creds)

    # 4. Fetch articles
    news_articles = get_news_articles()
    if not news_articles:
        print("No new articles to post.")
        return

    # 5. Post to the target blog only
    print(f"\n--- Processing Posts for Blog ID: {target_blog} ---")
    for article in news_articles:
        unique_post_id = f"{target_blog}:{article['url']}"
        
        if unique_post_id in posted_history:
            print(f"Skipping (Already Posted to this blog): {article['title'][:40]}...")
            continue
        
        try:
            body = {"title": article['title'], "content": article['content']}
            service.posts().insert(blogId=target_blog, body=body, isDraft=False).execute()
            print(f"✅ Successfully posted: {article['title'][:40]}...")
            
            # Record success
            posted_history.append(unique_post_id)
            save_history(posted_history)
            
            # Tiny safety delay between the two articles, but no big delays!
            time.sleep(5)
            
        except HttpError as error:
            print(f"❌ Error posting to {target_blog}: {error}")

    print("\n🎉 Run finished successfully!")

if __name__ == '__main__':
    main()

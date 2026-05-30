import os
import time
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def get_news_articles():
    """Fetches top headlines from NewsAPI."""
    news_api_key = os.environ.get('NEWS_API_KEY')
    if not news_api_key:
        print("⚠️ No NEWS_API_KEY found. Using dummy data for testing.")
        return [
            {"title": "Test Article 1", "content": "This is a test post to verify the Blogger bot."},
            {"title": "Test Article 2", "content": "Another test post confirming the loop works."}
        ]

    print("Fetching latest news from News API...")
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        # Grab the top 5 articles to prevent overloading the blog
        for item in data.get('articles', [])[:5]:
            # Skip articles that were removed or are missing content
            if item['title'] == '[Removed]' or not item['content']:
                continue
                
            # Format the content nicely for Blogger
            html_content = f"""
            <p><i>Source: {item['source']['name']}</i></p>
            <p>{item['description'] or ''}</p>
            <p>{item['content']}</p>
            <p><a href="{item['url']}" target="_blank">Read the full story here</a></p>
            """
            
            articles.append({
                "title": item['title'],
                "content": html_content
            })
            
        print(f"Successfully fetched {len(articles)} articles.")
        return articles
        
    except Exception as e:
        print(f"❌ Failed to fetch news: {e}")
        return []

def main():
    # 1. Load Credentials from GitHub Secrets
    CLIENT_ID = os.environ.get('CLIENT_ID')
    CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
    REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
    
    # Get Blogger IDs and clean up any spaces
    raw_blogger_ids = os.environ.get('BLOGGER_IDS', '')
    BLOGGER_IDS = [b_id.strip() for b_id in raw_blogger_ids.split(',') if b_id.strip()]

    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BLOGGER_IDS]):
        print("❌ CRITICAL ERROR: Missing one or more environment variables.")
        return

    # 2. Authenticate with Google
    print("Authenticating with Google Blogger API...")
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )

    service = build('blogger', 'v3', credentials=creds)

    # 3. Get the Content
    news_articles = get_news_articles()
    
    if not news_articles:
        print("No articles to post today. Exiting.")
        return

    # 4. The Safe Posting Loop (Prevents Error 429)
    for blog_id in BLOGGER_IDS:
        print(f"\n--- Starting posts for Blog ID: {blog_id} ---")
        
        for article in news_articles:
            body = {
                "title": article['title'],
                "content": article['content']
            }
            
            try:
                # Send the post to Blogger
                request = service.posts().insert(blogId=blog_id, body=body, isDraft=False)
                response = request.execute()
                print(f"✅ Successfully posted: {article['title']}")
                
                # Wait 15 seconds before the next post
                time.sleep(15)
                
            except HttpError as error:
                print(f"❌ Error posting '{article['title']}' to {blog_id}: {error}")
                
                # If we hit a rate limit, pause for 60 seconds
                if error.resp.status == 429:
                    print("⚠️ Hit a rate limit! Pausing for 60 seconds...")
                    time.sleep(60)
                # If it's a 403 or 401, the token/permissions are wrong
                elif error.resp.status in [401, 403]:
                    print("⚠️ Authentication/Permission error. Stopping this blog.")
                    break # Stop trying to post to this specific blog

    print("\n🎉 All automation tasks completed successfully!")

if __name__ == '__main__':
    main()

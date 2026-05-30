import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1. Load Credentials from GitHub Secrets
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
BLOGGER_IDS = os.environ.get('BLOGGER_IDS').split(',') # Assuming comma-separated IDs

# 2. Authenticate with Google
creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri='https://oauth2.googleapis.com/token',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

service = build('blogger', 'v3', credentials=creds)

# ---------------------------------------------------------
# 3. YOUR NEWS GATHERING CODE GOES HERE
# (Fetch from News API, format the text, etc.)
# 
# For this example, let's assume you have a list of 
# dictionary items called 'news_articles'
# ---------------------------------------------------------

news_articles = [
    {"title": "Breaking News 1", "content": "Full article text here..."},
    {"title": "Breaking News 2", "content": "Full article text here..."},
    # ... more articles
]

# 4. The Safe Posting Loop (Prevents Error 429)
for blog_id in BLOGGER_IDS:
    blog_id = blog_id.strip() # Clean up any accidental spaces
    print(f"Starting to post to Blog ID: {blog_id}")
    
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
            
            # --- THE CRITICAL DELAY ---
            # Wait 15 seconds before the next post to prevent the 429 Quota Error
            print("Taking a 15-second break to respect Google API limits...")
            time.sleep(15)
            
        except HttpError as error:
            print(f"❌ Error posting to {blog_id}: {error}")
            
            # If we STILL hit a rate limit, wait a full minute before trying the next one
            if error.resp.status == 429:
                print("Hit a rate limit! Pausing for 60 seconds...")
                time.sleep(60)

print("All posting tasks completed!")

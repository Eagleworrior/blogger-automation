import os
import json
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- CONFIGURATION ---
BLOGGER_IDS = os.environ.get('BLOGGER_IDS').split(',')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
HISTORY_FILE = 'posted_history.json'

# --- AUTH ---
creds = Credentials(
    None,
    refresh_token=os.environ.get('REFRESH_TOKEN'),
    client_id=os.environ.get('CLIENT_ID'),
    client_secret=os.environ.get('CLIENT_SECRET'),
    token_uri="https://oauth2.googleapis.com/token"
)
blogger = build('blogger', 'v3', credentials=creds)

def get_posted_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f: return json.load(f)
    return []

def save_posted_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history, f)

def fetch_news():
    url = f"https://newsdata.io/api/1/latest?apikey={NEWS_API_KEY}&language=en&category=technology"
    response = requests.get(url).json()
    return response.get('results', [])

def post_to_blogger(blog_id, item):
    body = {'title': item['title'], 'content': f"{item.get('description', '')} <br><br> Read more: {item['link']}"}
    blogger.posts().insert(blogId=blog_id, body=body).execute()

# --- MAIN LOGIC ---
history = get_posted_history()
news_items = fetch_news()

# Filter: Only keep news we haven't posted yet
new_news = [n for n in news_items if n['link'] not in history]

# Post 5 items per blog (if available)
for blog_id in BLOGGER_IDS:
    count = 0
    for item in new_news:
        if count >= 5: break
        try:
            post_to_blogger(blog_id, item)
            history.append(item['link'])
            count += 1
        except Exception as e:
            print(f"Error posting to {blog_id}: {e}")

save_posted_history(history)

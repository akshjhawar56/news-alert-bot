
import os
import json
import argparse
import feedparser
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import google.generativeai as genai
import time

# Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'topics.json')
HISTORY_PATH = os.path.join(os.path.dirname(__file__), 'history.json')
DIGEST_QUEUE_PATH = os.path.join(os.path.dirname(__file__), 'digest_queue.json')

# API Keys (Environment Variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", EMAIL_USER)

def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return default if default is not None else {}

def save_json(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {path}: {e}")

def fetch_news(topic):
    encoded_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    return feed.entries

def analyze_article(article, topic):
    """
    Uses Gemini to rate urgency:
    10: Extreme Global Catastrophe (War, Crash, Major Disaster)
    5: Relevant to topic
    1: Irrelevant
    """
    if not GEMINI_API_KEY:
        print("Skipping AI analysis (No API Key)")
        return {"urgency": 5, "reason": "No API Key"}

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')

    prompt = f"""
    Analyze this news headline for topic '{topic}': "{article.title}"
    
    Task: Rate urgency on scale 1-10.
    10 = EXTREME GLOBAL EMERGENCY (War declared, Stock market crashing NOW, Major natural disaster killing thousands).
    9 = Very high urgency, immediate attention required.
    5-8 = Major news for the topic, but not a global emergency.
    1-4 = Minor update or opinion piece.
    
    Return ONLY a JSON string: {{"urgency": <int>, "reason": "<short_string>"}}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up code blocks if present
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
             text = text[3:-3]
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Default to neutral urgency on error to be safe
        return {"urgency": 5, "reason": "Error analyzing"}

def send_email(subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("Skipping email (No Credentials)")
        print(f"Subject: {subject}")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Email failed: {e}")

def run_check_mode():
    print(f"Starting CHECK Mode at {datetime.now()}")
    
    config = load_json(CONFIG_PATH, {"topics": []})
    history = load_json(HISTORY_PATH, {"seen_ids": []})
    digest_queue = load_json(DIGEST_QUEUE_PATH, {"articles": []})
    
    # Ensure structure exist (migration fix)
    if "articles" not in digest_queue: digest_queue["articles"] = []
    if "seen_ids" not in history: history["seen_ids"] = []

    
    for topic in config.get("topics", []):
        print(f"Checking topic: {topic}")
        try:
            entries = fetch_news(topic)
        except Exception as e:
            print(f"Error fetching news for {topic}: {e}")
            continue
        
        # Check top 5 articles per topic to save API quota
        for entry in entries[:5]:
            if entry.id in history['seen_ids']:
                continue
            
            # Simple deduplication based on title similarity could go here
            # For now relying on ID
            
            print(f"  Analyzing: {entry.title}")
            analysis = analyze_article(entry, topic)
            urgency = analysis.get('urgency', 0)
            
            print(f"  > Urgency: {urgency}")
            
            # Log as seen immediately to avoid re-processing on crash
            history['seen_ids'].append(entry.id)
            
            link = entry.link
            
            if urgency >= 9:
                # BREAKING NEWS -> Send Instant Email
                print("  !!! BREAKING NEWS FOUND !!!")
                subject = f"🚨 BREAKING: {entry.title}"
                body = f"""
                <h1>🚨 {entry.title}</h1>
                <p><strong>Topic:</strong> {topic}</p>
                <p><strong>Urgency:</strong> {urgency}/10</p>
                <p><strong>Analysis:</strong> {analysis.get('reason')}</p>
                <p><a href="{link}">Read Full Article</a></p>
                """
                send_email(subject, body)
                
            elif urgency >= 4:
                # RELEVANT -> Add to Digest Queue
                print("  -> Added to digest queue")
                digest_queue['articles'].append({
                    "title": entry.title,
                    "link": link,
                    "topic": topic,
                    "reason": analysis.get('reason'),
                    "urgency": urgency,
                    "time": str(datetime.now())
                })
            else:
                print("  -> Ignored (low urgency)")

            # Sleep to respect rate limits (15 RPM = 4s, stay safer with 10s)
            time.sleep(10) 
    
    # Save State
    # Keep history manageable (last 1000 items)
    if len(history['seen_ids']) > 1000:
        history['seen_ids'] = history['seen_ids'][-1000:]
        
    save_json(HISTORY_PATH, history)
    save_json(DIGEST_QUEUE_PATH, digest_queue)
    print("Check complete.")

def run_digest_mode():
    print(f"Starting DIGEST Mode at {datetime.now()}")
    digest_queue = load_json(DIGEST_QUEUE_PATH, {"articles": []})
    
    if not digest_queue.get("articles"):
        print("Digest queue is empty. No email sent.")
        return

    articles = digest_queue["articles"]
    print(f"Found {len(articles)} articles in queue.")
    
    # Sort by urgency (descending)
    articles.sort(key=lambda x: x.get("urgency", 0), reverse=True)
    
    # Build Email Body
    body = """
    <h1>Your Daily News Digest</h1>
    <p>Here are the top stories from your tracked topics today.</p>
    <hr>
    """
    
    for article in articles:
        body += f"""
        <div style="margin-bottom: 20px;">
            <h3><a href="{article['link']}">{article['title']}</a></h3>
            <p><strong>Topic:</strong> {article['topic']} | <strong>Urgency:</strong> {article.get('urgency')}/10</p>
            <p><i>{article.get('reason')}</i></p>
        </div>
        """
        
    body += "<hr><p>End of Digest</p>"
    
    send_email(f"📰 Daily Digest: {len(articles)} Stories", body)
    
    # Clear Queue
    digest_queue["articles"] = []
    save_json(DIGEST_QUEUE_PATH, digest_queue)
    print("Digest sent and queue cleared.")

def main():
    parser = argparse.ArgumentParser(description="News Alert Bot")
    parser.add_argument('--mode', choices=['check', 'digest'], default='check', help="Mode: 'check' for instant alerts, 'digest' for daily summary")
    args = parser.parse_args()
    
    if args.mode == 'check':
        run_check_mode()
    elif args.mode == 'digest':
        run_digest_mode()

if __name__ == "__main__":
    main()

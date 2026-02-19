# Implementation Plan - News Alert System

## Goal Description
Build a "set and forget" news monitoring system that:
1.  Sends **instant emails** ONLY for "Extreme Breaking News" (Wars, Market Crashes, Major Disasters).
2.   queues relevant news for **specific topics** into a **Daily Digest**.
3.  Runs 24/7 without the user's laptop, using **GitHub Actions** (Free Tier).
4.  Allows easy editing of tracked topics via a configuration file (`topics.json`).

## Architecture

### 1. News Source: Google News RSS
- **Why:** Free, real-time, no rate limits (within reason), and supports complex queries (e.g., `https://news.google.com/rss/search?q=Iran+US+relations`).
- **Library:** `feedparser` (Python).

### 2. "Breaking" Intelligence: Google Gemini API
- **Problem:** Distinguishing "US attacks Iran" (Breaking) from "Opinion: Why US might attack Iran" (Not Breaking).
- **Solution:** Send article titles to Gemini Flash (fast & cheap/free tier).
- **Prompt:** "Rate the urgency of this news on a scale of 1-10. Is it a global catastrophe (war, crash, disaster)? If yes, set urgency=10. If it matches a user topic but is not catastrophic, set urgency=5."
- **Threshold:** Urgency >= 9 triggers instant email. Urgency 4-8 is appended to `digest_queue.json`. < 4 is ignored.

### 3. Notification: SMTP (Gmail)
- **Method:** Standard Python `smtplib`.
- **Auth:** User will need an "App Password" from their Google Account.

### 4. Deployment: GitHub Actions (Cron)
- **Schedule:**
    - **Breaking Checker:** Runs every 20 minutes (`*/20 * * * *`).
    - **Daily Digest:** Runs once a day (`0 18 * * *`).
- **State Management:**
    - **Digest Queue:** Store pending digest articles in `digest_queue.json` (committed to repo).
    - **History:** Track seen article IDs in `history.json` to prevent duplicates.

## Implementation Steps

### Phase 1: The Core Script (`news_bot.py`)
- `fetch_news(topic)`: Gets RSS feed.
- `analyze_news(article)`: Calls Gemini API.
- `send_email(subject, body)`: Sends via SMTP.
- `main()`: Orchestrates the logic.

### Phase 2: State Management
- `load_history()` / `save_history()`: Reads/Writes to `history.json` to track seen article IDs.

### Phase 3: Deployment
- `.github/workflows/check_news.yml`: The cron job definition.
- Secrets setup: `GEMINI_API_KEY`, `EMAIL_USER`, `EMAIL_PASS`.

## User Review Required
> [!IMPORTANT]
> **GitHub Actions Frequency:** The free tier of GitHub Actions is generous but technically "guarantees" are loose. A 15-20 min interval is usually safe. "Instant" here means "within 20 mins".

> [!WARNING]
> **Commit Noise:** To remember which news was already sent, the bot will auto-commit to your repo. Your commit history will have many "Update state" entries. I can squash them or we can use a Gist if preferred, but repo commit is simplest.

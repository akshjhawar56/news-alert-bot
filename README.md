# AI News Alert Bot

This bot monitors Google News 24/7 for specific topics and uses Google Gemini AI to filter for "Breaking News".

- **Breaking News (Urgency >= 9):** Sends an instant email.
- **Relevant News (Urgency >= 4):** Adds to a daily digest queue.
- **Daily Digest:** Sends a summary email every day at 6:30 PM IST.

## Configuration

Edit `config/topics.json` to change your tracked topics.

## Deployment (GitHub Actions)

This bot is designed to run on GitHub Actions for free.

### Setup Steps

1.  **Push this code to a new GitHub Repository.**
2.  **Go to Settings -> Secrets and variables -> Actions.**
3.  **Click "New repository secret"** and add the following 3 secrets:

| Name | Value |
| :--- | :--- |
| `GEMINI_API_KEY` | Your Google AI Studio API Key |
| `EMAIL_USER` | Your Gmail address (e.g., `aksh...@gmail.com`) |
| `EMAIL_PASS` | Your Gmail App Password (16-letter code) |
| `EMAIL_RECEIVER` | (Optional) Comma-separated list of emails to receive alerts (e.g. `me@gmail.com, you@gmail.com`). Defaults to sending to yourself. |

4.  **Enable Actions:** Go to the "Actions" tab in your repo and enable workflows if asked.
5.  **Done!** The bot will check for news every 20 minutes automatically.

### Manual Trigger
You can force a run by going to the "Actions" tab -> "News Alert Bot" -> "Run workflow".

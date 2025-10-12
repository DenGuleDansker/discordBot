# Discord Bot (n8n integration)

A small Discord bot that forwards user questions to an n8n webhook and returns responses. This README explains the project, required packages, environment variables and how to run the bot (including Docker & Docker Compose).

---

## Features
- Trigger via `!chat` command or by mentioning the bot (e.g. `@N8N-ChatBot What is the largest planet?`)
- Forwards a JSON payload to an n8n webhook with:
  - `question`, `userName`, `channelId`, `sessionId`
- Returns the webhook reply to the Discord channel
- Session IDs per user (simple in-memory store)
- Secure defaults: blocks automatic mentions in returned text

---

## Files of interest
- `bot.py` — your Discord bot implementation
- `Dockerfile` — how to build the container image
- `docker-compose.yml` — convenient compose file to run the bot
- `requirements.txt` — Python dependencies
- `.env.example` — example environment variables

---

## Requirements

Create a `requirements.txt` (place next to `Dockerfile` and `bot.py`):

discord.py>=2.3.2
aiohttp>=3.8.0
python-dotenv>=0.20.0
---

## Environment (.env)

Copy `.env.example` to `.env` and fill in your values:

Discord bot tokenTOKEN=your_discord_bot_token_hereWebhook to post to (dev)WEBHOOK_URL=http://ip:port/webhook-test/callOptional production webhook overrideWEBHOOK_URL_PRODUCTION=https://your-production-webhookOptional secret header sent to the webhook (if you require one)WEBHOOK_SECRET=mithemmeligetoken
Important:
- NEVER commit your `.env` to Git. Add `.env` to `.gitignore`.
- If you accidentally commit a secret, rotate it immediately (e.g., regenerate your Discord token) and remove it from Git history.

---

## Quick start (local / development)

1. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

Install dependencies:
pip install -r requirements.txt


Create .env using the example and fill in your TOKEN and WEBHOOK_URL.


Run the bot:

python bot.py
Docker (recommended for deployment)Build and run using Docker Compose:

Ensure .env file exists in the project folder.


Build and start:

docker compose up --build -d

View logs:
docker compose logs -f discord-bot

Stop:
docker compose down
Notes:
If your webhook is on the same host and you use a LAN IP (e.g. 192.168.x.x), containers should normally reach it. If not, consider network_mode: "host" on Linux or expose/forward the webhook publicly (ngrok) for testing.
The Dockerfile creates a non-root user to run the bot.
Security & best practices
Add .env to .gitignore to prevent accidental commits:
echo ".env" >> .gitignore
git add .gitignore && git commit -m "Ignore .env"


Never push tokens/secrets to GitHub. If you do, immediately:

Revoke/regenerate the compromised token.
Remove the secret from Git history (use git filter-repo or BFG).


Use GitHub Secrets / environment variables in CI/CD for secure deployments.
Use WEBHOOK_SECRET or another header to authenticate requests your webhook receives.
Troubleshooting
Bot doesn't respond:

Ensure TOKEN is correct and bot is invited to the guild with proper permissions.
Ensure "Message Content Intent" is enabled in Discord Developer Portal if you rely on message content.


Webhook POST fails:

Verify the webhook URL is reachable from the machine/container running the bot (use curl).
Check n8n workflow for unused Respond to Webhook nodes or errors.


Push blocked on GitHub due to secret scanning:

Rotate the secret and clean your git history (see Security section).


Example payload sent to webhookWhen a user triggers the bot, the webhook receives JSON like:{
  "question": "Hej, hvad er den største planet",
  "userName": "123456789012345678",
  "channelId": "987654321098765432",
  "sessionId": "SESSION-<uuid>"
}
Your n8n flow should return JSON such as:{
  "reply": "Jupiter is the largest planet in our Solar System."
}
If reply is empty or absent, the bot will send nothing back (or a minimal error string depending on your configuration).Contributing
Keep secrets out of commits.
Add tests for any logic changes (session handling, mention conversion, etc.).
Open an issue / PR with clear description and reproduction steps.
LicenseChoose a license for your project (e.g. MIT). Add LICENSE file to your repository.If you want, I can:
Produce a ready-to-copy README.md file (I can output it as a file you can paste),
Add example docker-compose.yml and Dockerfile snippets directly into the README,
Translate the README to Danish.
Which would you like next?

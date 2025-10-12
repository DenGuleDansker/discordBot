# ==============================================================
# requirements.txt
# (put this file next to Dockerfile and bot.py)
# ==============================================================
discord.py>=2.3.2
aiohttp>=3.8.0
python-dotenv>=0.20.0

# ==============================================================
# .env.example
# Copy to .env and fill in values
# ==============================================================
# Discord bot token
TOKEN=your_discord_bot_token_here

# Webhook to post to (dev)
WEBHOOK_URL=http://ip:port/webhook-test/call

# Optional production webhook override
# WEBHOOK_URL_PRODUCTION=https://your-production-webhook

# discordBot

import discord
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import uuid
import re

load_dotenv()

# Choose production webhook if available, otherwise fallback to dev/test webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL_PRODUCTION") or os.getenv("WEBHOOK_URL")
if WEBHOOK_URL:
    print(f"Using webhook URL: {WEBHOOK_URL}")
else:
    raise RuntimeError("Ingen WEBHOOK_URL_PRODUCTION eller WEBHOOK_URL sat i .env")

# Session storage: gem en sessionId pr. bruger (kan udvides til DB)
user_sessions = {}

# Create a Discord client instance and set the command prefix
intents = discord.Intents.all()  # Sørg for Message Content Intent er aktiveret i Developer Portal
bot = commands.Bot(command_prefix='!', intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.event
async def on_command_error(ctx, error):
    error_message = f'Error occured while processing command: {error}'
    logging.error(error_message)
    try:
        await ctx.send(error_message)
    except Exception:
        pass

# Hjælpefunktion: send payload til webhook og returner reply-text (eller fejltekst)
async def forward_to_webhook_and_get_reply(question: str, user_id: str, channel_id: str):
    # Genbrug sessionId for brugeren, eller opret ny hvis ikke eksisterer
    session_id = user_sessions.get(user_id)
    if not session_id:
        session_id = f"SESSION-{uuid.uuid4()}"
        user_sessions[user_id] = session_id

    payload = {
        "question": question,
        "userName": user_id,
        "channelId": channel_id,
        "sessionId": session_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"}) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        reply_text = data.get("reply") or ""
                    except Exception:
                        reply_text = ""
                    return reply_text
                else:
                    text = await resp.text()
                    logging.error(f"Webhook returned {resp.status}: {text}")
                    return "Der skete en fejl ved at sende til webhook (ikke 200)."
    except Exception:
        logging.exception("Fejl ved POST til webhook")
        return "Fejl ved at kontakte webhook. Prøv igen senere."

# !chat kommandoen (bevarer eksisterende funktionalitet)
@bot.command(name='chat')
async def chat(ctx, *, question: str = None):
    if not question:
        await ctx.send("Skriv venligst dit spørgsmål efter !chat, fx: !chat Hvad er den største planet?")
        return

    user_id = str(ctx.author.id)
    channel_id = str(ctx.channel.id)

    reply_text = await forward_to_webhook_and_get_reply(question, user_id, channel_id)

    # SEND KUN svaret (ingen mention). Bloker mentions i output for sikkerhed.
    allowed = discord.AllowedMentions(users=False, roles=False, everyone=False)
    await ctx.send(reply_text, allowed_mentions=allowed)

# Lyt efter mention: når botten nævnes i en besked, brug resten som spørgsmål
@bot.event
async def on_message(message):
    # Ignorer beskeder fra bots (inkl. sig selv)
    if message.author.bot:
        return

    # Hvis botten nævnes i message.mentions -> behandl som chat
    if bot.user in message.mentions:
        # Fjern mention-strings (<@123...> og <@!123...>) fra indholdet
        content = message.content
        content_without_mention = re.sub(rf'<@!?\s*{bot.user.id}\s*>', '', content)
        question = content_without_mention.strip()

        if not question:
            # Hvis brugeren kun nævnte botten uden tekst, giv en hurtig besked om hvordan
            hint = f"Skriv dit spørgsmål efter mention, fx: @{bot.user.name} Hvad er den største planet?"
            allowed = discord.AllowedMentions(users=False, roles=False, everyone=False)
            await message.channel.send(hint, allowed_mentions=allowed)
        else:
            user_id = str(message.author.id)
            channel_id = str(message.channel.id)
            reply_text = await forward_to_webhook_and_get_reply(question, user_id, channel_id)

            # SEND KUN svaret (ingen mention). Bloker mentions i output for sikkerhed.
            allowed = discord.AllowedMentions(users=False, roles=False, everyone=False)
            await message.channel.send(reply_text, allowed_mentions=allowed)

    # VIGTIGT: tillad commands at fungere som normalt
    await bot.process_commands(message)

# Valgfri: kommando til at nulstille session for brugeren
@bot.command(name='reset_session')
async def reset_session(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_sessions:
        del user_sessions[user_id]
        await ctx.send("Din session er nulstillet.")
    else:
        await ctx.send("Du havde ingen aktiv session.")

# Kør botten
bot.run(os.getenv('TOKEN'))
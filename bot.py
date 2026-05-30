import discord
import os
import logging
import asyncio
import re
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY er ikke sat i .env")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.1-flash-lite")

# Gem samtalehistorik pr. bruger
user_chats: dict[str, genai.ChatSession] = {}

intents = discord.Intents.all()
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
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')


@bot.event
async def on_command_error(ctx, error):
    logging.error(f'Command error: {error}')
    try:
        await ctx.send(f'Fejl: {error}')
    except Exception:
        pass


async def ask_gemini(question: str, user_id: str) -> str:
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])

    chat = user_chats[user_id]
    try:
        response = await asyncio.to_thread(chat.send_message, question)
        return response.text
    except Exception:
        logging.exception("Fejl ved Gemini API-kald")
        return "Fejl ved at kontakte Gemini. Prøv igen senere."


@bot.command(name='chat')
async def chat(ctx, *, question: str = None):
    if not question:
        await ctx.send("Skriv dit spørgsmål efter !chat, fx: !chat Hvad er den største planet?")
        return

    reply = await ask_gemini(question, str(ctx.author.id))
    allowed = discord.AllowedMentions(users=False, roles=False, everyone=False)
    await ctx.send(reply, allowed_mentions=allowed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        content = re.sub(rf'<@!?\s*{bot.user.id}\s*>', '', message.content).strip()

        if not content:
            await message.channel.send(
                f"Skriv dit spørgsmål efter mention, fx: @{bot.user.name} Hvad er den største planet?",
                allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
            )
        else:
            reply = await ask_gemini(content, str(message.author.id))
            await message.channel.send(
                reply,
                allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False)
            )

    await bot.process_commands(message)


@bot.command(name='reset')
async def reset(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_chats:
        del user_chats[user_id]
        await ctx.send("Din samtalehistorik er nulstillet.")
    else:
        await ctx.send("Du havde ingen aktiv samtale.")


bot.run(os.getenv('TOKEN'))

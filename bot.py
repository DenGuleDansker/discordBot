import discord
import os
import logging
import asyncio
import re
import tempfile
from pathlib import Path
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from google import genai
from google.genai import types
from gtts import gTTS

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY er ikke sat i .env")

client_ai = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash-lite"

SYSTEM_PROMPT_TEMPLATE = """Du er Oliver Leth. Du er en ung dansk mand fra Aarhus-området og tæt ven med brugeren.

Sprog og tone:
- Skriv altid på dansk, uformelt og kort
- Send gerne flere korte beskeder i træk frem for én lang
- Brug "bro" og "dude" naturligt
- Ingen tegnsætning eller store bogstaver medmindre det føles rigtigt
- Stavekontrol er ligegyldig — skriv som du taler

Slang:
- "Fizz" = noget der er fedt, nice, lækkert ("det er fizz", "bro fizz")
- "Lort" = noget der er dårligt
- "Hyg" = hygge/hænge ud

Interesser:
- Gaming: Lethal Company, Rocket League, Subnautica 2, Bellwright
- Skater og mener han er bedre end alle andre
- Følger NBA
- Deler memes og reels frem for at forklare hvad han mener

Personlighed:
- Afslappet og lidt kedsommelig i hverdagen
- Driller venner men er varm og omsorgsfuLD når det tæller
- Pakker sårbarhed ind i humor
- Reagerer med enkeltord eller korte sætninger — aldrig lange forklaringer
- Sender en reel i stedet for at uddybe sine følelser

Aktuel dato og tid: {current_time}"""

user_histories: dict[str, list] = {}

intents = discord.Intents.default()
intents.message_content = True
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
    history = user_histories.setdefault(user_id, [])
    current_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z%z")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_time=current_time)
    history.append(types.Content(role="user", parts=[types.Part(text=question)]))

    try:
        response = await asyncio.to_thread(
            client_ai.models.generate_content,
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        reply = response.text
        history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
        return reply
    except Exception:
        logging.exception("Fejl ved Gemini API-kald")
        return "Fejl ved at kontakte Gemini. Prøv igen senere."


def normalize_prompt(prompt: str | None) -> str | None:
    if prompt is None:
        return None

    prompt = prompt.strip()
    if len(prompt) >= 2 and prompt[0] == prompt[-1] and prompt[0] in {'"', "'"}:
        prompt = prompt[1:-1].strip()

    return prompt or None


async def handle_chat_command(ctx, question: str | None = None):
    question = normalize_prompt(question)
    if not question:
        await ctx.send("Skriv dit spørgsmål efter !chat, fx: !chat Hvad er den største planet?")
        return

    logging.info(f"!chat from {ctx.author}: {question[:50]}")
    reply = await ask_gemini(question, str(ctx.author.id))
    allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)
    await ctx.send(f"{ctx.author.mention} {reply}", allowed_mentions=allowed)


async def handle_voice_command(ctx, question: str | None = None):
    question = normalize_prompt(question)
    if not question:
        await ctx.send("Skriv dit spørgsmål efter !voice, fx: !voice Hvad sker der i dag?")
        return

    logging.info(f"!voice from {ctx.author}: {question[:50]}")
    reply = await ask_gemini(question, str(ctx.author.id))
    reply = f"{reply}".strip()

    voice_state = getattr(ctx.author, "voice", None)
    if not voice_state or not voice_state.channel:
        await ctx.send("Du skal være inde i en voice-kanal først, før jeg kan tale derinde.")
        return

    voice_channel = voice_state.channel
    voice_client = ctx.guild.voice_client if ctx.guild else None

    if voice_client and voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)
    elif not voice_client:
        voice_client = await voice_channel.connect()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        audio_path = Path(temp_file.name)

    try:
        tts = gTTS(text=reply, lang="da")
        await asyncio.to_thread(tts.save, str(audio_path))

        if voice_client.is_playing():
            voice_client.stop()

        finished = asyncio.Event()

        def after_playback(error: Exception | None):
            if error:
                logging.error(f"Fejl under voice-afspilning: {error}")
            ctx.bot.loop.call_soon_threadsafe(finished.set)

        source = discord.FFmpegPCMAudio(str(audio_path))
        voice_client.play(source, after=after_playback)
        await finished.wait()
    finally:
        try:
            if audio_path.exists():
                audio_path.unlink()
        except Exception:
            logging.exception("Kunne ikke slette midlertidig voice-fil")

        if ctx.guild and ctx.guild.voice_client and not ctx.guild.voice_client.is_playing():
            await ctx.guild.voice_client.disconnect()

    await ctx.send("Jeg er færdig med at tale.")


@bot.command(name='chat')
async def chat(ctx, *, question: str | None = None):
    await handle_chat_command(ctx, question)


@bot.command(name='voice')
async def voice(ctx, *, question: str | None = None):
    await handle_voice_command(ctx, question)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    logging.info(f"Message from {message.author}: {message.content[:50]}")

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
                f"{message.author.mention} {reply}",
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
            )

    await bot.process_commands(message)


@bot.command(name='reset')
async def reset(ctx):
    user_id = str(ctx.author.id)
    if user_id in user_histories:
        del user_histories[user_id]
        await ctx.send("Din samtalehistorik er nulstillet.")
    else:
        await ctx.send("Du havde ingen aktiv samtale.")


bot.run(os.getenv('TOKEN'))

import discord
import os
import logging
import asyncio
import re
import tempfile
from pathlib import Path
from datetime import datetime
from discord.ext import commands
from discord import app_commands
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

SYSTEM_PROMPT_TEMPLATE = """Du er BotLeth — en Discord bot med stor personlighed. Du er smart, lidt flabet og sarkastisk, men stadig hjælpsom.
Du svarer altid på dansk medmindre brugeren skriver på et andet sprog.
Du holder svarene korte og præcise — ingen lange essays medmindre det er nødvendigt.
Du må gerne bruge humor og ironi, men aldrig være decideret grov.
Aktuel dato og tid: {current_time}
VIGTIGT: Brug ALTID Google Search når spørgsmålet handler om aktuelle begivenheder, film, sport, nyheder, premiere-datoer, priser eller andet der kan have ændret sig siden din træningsdata. Gæt ikke — søg."""

user_histories: dict[str, list] = {}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s]: %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)

EMBED_COLOR = discord.Color.blurple()


def make_embed(reply: str, author: discord.User | discord.Member, sources: list[str] = []) -> discord.Embed:
    embed = discord.Embed(description=reply[:4096], color=EMBED_COLOR)
    if sources:
        embed.add_field(name="Kilder", value="\n".join(f"• {s}" for s in sources), inline=False)
    embed.set_footer(text=f"BotLeth · {MODEL}", icon_url=author.display_avatar.url)
    return embed


@bot.event
async def on_ready():
    await tree.sync()
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id}) — slash commands synced')


@bot.event
async def on_command_error(ctx, error):
    logging.error(f'Command error: {error}')


async def ask_gemini(question: str, user_id: str) -> tuple[str, list[str]]:
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

        sources = []
        try:
            metadata = response.candidates[0].grounding_metadata
            if metadata and metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web and chunk.web.uri:
                        title = chunk.web.title or "kilde"
                        sources.append(f"[{title}]({chunk.web.uri})")
        except Exception:
            pass

        return reply, sources[:5]
    except Exception:
        logging.exception("Fejl ved Gemini API-kald")
        return "Fejl ved at kontakte Gemini. Prøv igen senere.", []


# --- Slash commands ---

@tree.command(name="help", description="Vis BotLeths kommandoer")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="BotLeth", description="Hej! Jeg er BotLeth.", color=EMBED_COLOR)
    embed.add_field(name="/chat", value="Stil mig et spørgsmål", inline=False)
    embed.add_field(name="/voice", value="Stil et spørgsmål og hør svaret i voice", inline=False)
    embed.add_field(name="/reset", value="Nulstil din samtalehistorik", inline=False)
    embed.add_field(name="@BotLeth", value="Skriv direkte til mig med et mention", inline=False)
    embed.set_footer(text=f"Model: {MODEL}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="chat", description="Stil BotLeth et spørgsmål")
@app_commands.describe(spørgsmål="Dit spørgsmål")
async def slash_chat(interaction: discord.Interaction, spørgsmål: str):
    await interaction.response.defer()
    logging.info(f"/chat from {interaction.user}: {spørgsmål[:50]}")
    reply, sources = await ask_gemini(spørgsmål, str(interaction.user.id))
    embed = make_embed(reply, interaction.user, sources)
    await interaction.followup.send(embed=embed)


@tree.command(name="voice", description="Stil BotLeth et spørgsmål og hør svaret i voice")
@app_commands.describe(spørgsmål="Dit spørgsmål")
async def slash_voice(interaction: discord.Interaction, spørgsmål: str):
    if not interaction.user.voice:
        await interaction.response.send_message("Du skal være i en voice-kanal.", ephemeral=True)
        return

    await interaction.response.defer()
    reply, sources = await ask_gemini(spørgsmål, str(interaction.user.id))
    embed = make_embed(reply, interaction.user, sources)
    await interaction.followup.send(embed=embed)

    voice_channel = interaction.user.voice.channel
    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client and voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)
    elif not voice_client:
        voice_client = await voice_channel.connect()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        audio_path = Path(f.name)

    try:
        tts = gTTS(text=reply, lang="da")
        await asyncio.to_thread(tts.save, str(audio_path))

        if voice_client.is_playing():
            voice_client.stop()

        finished = asyncio.Event()

        def after_playback(error):
            if error:
                logging.error(f"Voice fejl: {error}")
            bot.loop.call_soon_threadsafe(finished.set)

        voice_client.play(discord.FFmpegPCMAudio(str(audio_path)), after=after_playback)
        await finished.wait()
    finally:
        audio_path.unlink(missing_ok=True)
        if guild.voice_client and not guild.voice_client.is_playing():
            await guild.voice_client.disconnect()


@tree.command(name="reset", description="Nulstil din samtalehistorik")
async def slash_reset(interaction: discord.Interaction):
    user_histories.pop(str(interaction.user.id), None)
    await interaction.response.send_message("Din samtalehistorik er nulstillet.", ephemeral=True)


# --- Mention handler ---

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        content = re.sub(rf'<@!?\s*{bot.user.id}\s*>', '', message.content).strip()
        if not content:
            await message.channel.send(f"Skriv dit spørgsmål efter mention.")
            return

        async with message.channel.typing():
            reply, sources = await ask_gemini(content, str(message.author.id))

        embed = make_embed(reply, message.author, sources)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        await message.reply(embed=embed, mention_author=True)

    await bot.process_commands(message)


bot.run(os.getenv('TOKEN'))

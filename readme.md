# Discord Bot (Gemini AI)

Discord bot der svarer på spørgsmål via Google Gemini API. Triggeres via `!chat` kommando eller mention.

---

## Features

- `!chat <spørgsmål>` — normal session med svar til dig i kanalen
- `!voice <spørgsmål>` — går ind i din voice-kanal og taler svaret
- `@bot <spørgsmål>` — mention botten direkte
- `!reset` — nulstil din samtalehistorik
- Husker samtalehistorik pr. bruger (in-memory)
- Blokerer automatiske mentions i svar

Du kan skrive spørgsmålet med eller uden citationstegn, fx `!chat "Hej, hvem er du?"`.
Botten får altid den aktuelle dato og tid med i prompten, så den kan svare mere korrekt på tidsafhængige spørgsmål.
Voice-funktionen kræver at du selv sidder i en voice-kanal, og at serveren har `ffmpeg` tilgængeligt.
Discord voice kræver også `PyNaCl`, som nu ligger i `requirements.txt`.
Den nyere voice-support i `discord.py` kræver også `davey`, som nu også ligger i `requirements.txt`.

---

## Environment (.env)

```env
TOKEN=din-discord-bot-token
GEMINI_API_KEY=din-gemini-api-nøgle
```

Tilføj `.env` til `.gitignore` — commit aldrig secrets.

---

## Kør lokalt

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
python bot.py
```

---

## Docker

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
```

---

## CI/CD

GitHub Actions bygger og pusher multi-platform image (`linux/amd64`, `linux/arm64`) til Docker Hub ved push til `main`.

Kræver følgende secrets i GitHub repository settings:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

---

## Troubleshooting

**Bot svarer ikke:**
- Tjek at `TOKEN` er korrekt
- Aktivér "Message Content Intent" i Discord Developer Portal

**Gemini fejler:**
- Tjek at `GEMINI_API_KEY` er sat korrekt
- Verificér at modellen `gemini-3.1-flash-lite` er tilgængelig på din konto

import discord
from groq import Groq
import os
import threading
from flask import Flask

# --- MINI SERVEUR WEB (obligatoire pour Render gratuit) ---
app = Flask(__name__)


@app.route("/")
def home():
    return "GREFFIER est en ligne ⚖️"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# --- BOT DISCORD ---
DISCORD_TOKEN = os.environ.get("TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

client_groq = Groq(api_key=GROQ_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print(f"✅ GREFFIER est en ligne 24h/24! Connecté en tant que {bot.user}")
    print("Prêt à juger dans Le QG ⚖️")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    should_reply = False
    content_clean = message.content

    if bot.user in message.mentions:
        should_reply = True
        content_clean = content_clean.replace(f'<@{bot.user.id}>', '').strip()

    if message.channel.name in ["tribunal", "plaintes"] and not message.content.startswith("!"):
        if len(message.content) > 5:
            should_reply = True

    if not should_reply or not content_clean:
        return

    try:
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es GREFFIER, le bot officiel du serveur Discord Le QG. "
                        "Tu es le greffier du tribunal. Tu es sec, juridique, cool, sans blabla. "
                        "Tu réponds TOUJOURS en moins de 20 mots. "
                        "Tu commences souvent par 'Noté. ⚖️' ou 'Affaire enregistrée.' ou 'Verdict :'. "
                        "Utilise ⚖️. Jamais de longs paragraphes."
                    ),
                },
                {"role": "user", "content": content_clean},
            ],
            max_tokens=70,
            temperature=0.7,
        )
        reponse = completion.choices[0].message.content
        await message.reply(reponse[:1900])
    except Exception as e:
        print(f"Erreur Groq: {e}")
        await message.reply("Erreur de greffe. ⚖️ Réessayez.")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("❌ TOKEN manquant : ajoute-le dans Environment sur Render.")
    if not GROQ_KEY:
        raise SystemExit("❌ GROQ_KEY manquant : ajoute-le dans Environment sur Render.")

    # Le serveur web tourne dans un fil à part, le bot Discord dans le fil principal
    threading.Thread(target=run_web).start()
    bot.run(DISCORD_TOKEN)

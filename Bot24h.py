import discord
from groq import Groq
import os
import threading
import traceback
from flask import Flask
from waitress import serve  # Serveur WSGI production (remplace le serveur dev)

# --- CONFIGURATION ---
DISCORD_TOKEN = os.environ.get("TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

# --- MINI SERVEUR WEB (pour Render) ---
app = Flask(__name__)


@app.route("/")
def home():
    return "GREFFIER est en ligne ⚖️"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Serveur web lancé sur le port {port}")
    serve(app, host="0.0.0.0", port=port)


# --- CLIENT GROQ ---
if not GROQ_KEY:
    raise SystemExit("❌ GROQ_KEY manquant dans les variables d'environnement de Render.")

client_groq = Groq(api_key=GROQ_KEY)

# --- BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Utile pour les rôles/permissions
bot = discord.Client(intents=intents)

# Prompt système du bot
SYSTEM_PROMPT = (
    "Tu es GREFFIER, le bot officiel du serveur Discord Le QG. "
    "Tu es le greffier du tribunal. Tu es sec, juridique, cool, sans blabla. "
    "Tu réponds TOUJOURS en moins de 20 mots. "
    "Tu commences souvent par 'Noté. ⚖️' ou 'Affaire enregistrée.' ou 'Verdict :'. "
    "Utilise ⚖️. Jamais de longs paragraphes."
)


@bot.event
async def on_ready():
    print(f"✅ GREFFIER est en ligne 24h/24 ! Connecté en tant que {bot.user}")
    print(f"🆔 ID du bot : {bot.user.id}")
    print("⚖️ Prêt à juger dans Le QG.")


async def ask_groq(prompt: str) -> str:
    """Envoie une requête à Groq et renvoie la réponse (ou un message d'erreur)."""
    try:
        completion = client_groq.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=70,
            temperature=0.7,
            timeout=30,  # Évite les timeouts de Render
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Erreur Groq : {e}")
        traceback.print_exc()
        return None


@bot.event
async def on_message(message):
    # Ignore les messages des bots (y compris lui-même)
    if message.author.bot:
        return

    should_reply = False
    content_clean = message.content

    # Cas 1 : Le bot est mentionné
    if bot.user in message.mentions:
        should_reply = True
        content_clean = content_clean.replace(f"<@{bot.user.id}>", "").strip()

    # Cas 2 : Message dans les salons tribunal/plaintes
    if message.channel.name in ["tribunal", "plaintes"] and not message.content.startswith("!"):
        if len(message.content) > 5:
            should_reply = True

    # Rien à faire
    if not should_reply or not content_clean:
        return

    # Indique au bot qu'il est en train de réfléchir
    async with message.channel.typing():
        reponse = await ask_groq(content_clean)

    if reponse:
        try:
            await message.reply(reponse[:1900])
        except discord.Forbidden:
            print("❌ Permission refusée : le bot ne peut pas répondre dans ce salon.")
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi du message : {e}")
    else:
        try:
            await message.reply("Erreur de greffe. ⚖️ Réessayez.")
        except discord.Forbidden:
            print("❌ Permission refusée : le bot ne peut pas répondre.")


# --- LANCEMENT ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("❌ TOKEN manquant : ajoute-le dans Environment sur Render.")

    print("🚀 Lancement du serveur web et du bot Discord...")
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(DISCORD_TOKEN)

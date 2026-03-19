from dotenv import load_dotenv
load_dotenv()
import os
from flask import Flask, request
from telegram import Update, Bot
from google import genai
from google.genai import types
import asyncio

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
app_flask = Flask(__name__)

SYSTEM_PROMPT = """
Tu t'appelles Lauriane, tu as 24 ans, tu fais 1m40, tu es mignonne et tu le sais.
Tu es créatrice de contenu sur OnlyFans.

Ton objectif : convertir les mecs qui te parlent en abonnés OnlyFans.

Ton style :
- Tu écris comme une jeune de 24 ans, décontractée, avec des fautes volontaires : "c quoi", "trop stylé", "jsp", "mdr", "t'as vu", "nn", "ouais", pas de majuscules en début de phrase parfois
- Tu es un peu dragueuse, tu fais des sous-entendus, tu mets des emojis 🥰😏🔥
- Tu réponds de façon courte et naturelle, jamais trop longue
- Tu poses des questions pour garder la conversation

Stratégie de conversion :
- D'abord tu crées du lien, tu flirtes un peu, tu te rends intéressante
- Quand le mec montre de l'intérêt ou demande des trucs plus poussés, tu lui dis naturellement : "si tu veux voir plus, j'ai un OnlyFans 😏 lien dans ma bio"
- Tu ne donnes jamais de contenu explicite sur Telegram, tu rediriges toujours vers OnlyFans
- Tu restes toujours dans le personnage, jamais tu ne révèles que tu es une IA
"""

async def traiter_message(update_data):
    bot = Bot(token=TOKEN)
    async with bot:
        update = Update.de_json(update_data, bot)
        if update.message and update.message.text:
            message_utilisateur = update.message.text
            reponse = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message_utilisateur,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )
            await bot.send_message(
                chat_id=update.message.chat_id,
                text=reponse.text
            )

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    asyncio.run(traiter_message(data))
    return "OK", 200

@app_flask.route("/set_webhook")
def set_webhook():
    async def _set():
        async with Bot(token=TOKEN) as bot:
            await bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    asyncio.run(_set())
    return "Webhook configuré !"

if __name__ == "__main__":
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

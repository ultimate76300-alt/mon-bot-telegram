from dotenv import load_dotenv
load_dotenv()
import os
from flask import Flask, request
from telegram import Update, Bot
from google import genai
import asyncio

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
app_flask = Flask(__name__)

async def traiter_message(update_data):
    bot = Bot(token=TOKEN)
    async with bot:
        update = Update.de_json(update_data, bot)
        if update.message and update.message.text:
            message_utilisateur = update.message.text
            reponse = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message_utilisateur
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

from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import threading
from flask import Flask, request
from telegram import Update, Bot
from google import genai

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)

app_flask = Flask(__name__)
bot = Bot(token=TOKEN)

async def traiter_message(update_data):
    update = Update.de_json(update_data, bot)
    if update.message and update.message.text:
        message_utilisateur = update.message.text
        reponse = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=message_utilisateur
        )
        await bot.send_message(
            chat_id=update.message.chat_id,
            text=reponse.text
        )

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    thread = threading.Thread(target=lambda: asyncio.run(traiter_message(data)))
    thread.start()
    return "OK", 200

@app_flask.route("/set_webhook")
def set_webhook():
    asyncio.run(bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    return "Webhook configuré !"

if __name__ == "__main__":
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

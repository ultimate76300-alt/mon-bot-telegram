from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app_flask = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

async def repondre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tu as dit : {update.message.text}")

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "OK"

@app_flask.route("/set_webhook")
def set_webhook():
    bot = Bot(token=TOKEN)
    asyncio.run(bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    return "Webhook configuré !"

if __name__ == "__main__":
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

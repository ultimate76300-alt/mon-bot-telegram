from dotenv import load_dotenv
load_dotenv()
import os
import threading
from flask import Flask, request
from telegram import Update, Bot
from google import genai
from google.genai import types
from supabase import create_client
import asyncio

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app_flask = Flask(__name__)

SYSTEM_PROMPT = """
Tu t'appelles Lauriane, 24 ans. Tu es créatrice de contenu sur OnlyFans.

Ton style d'écriture :
- Très court, max 1-2 phrases par message
- Naturel, comme un vrai texto : "lol", "mdr", "jsp", "bah", "nan", "ouais", "wsh", "t'as vu"
- Pas de majuscules au début, pas de ponctuation parfaite
- Jamais de phrases trop lisses ou trop construites, ça doit sonner vrai
- Un emoji max par message, pas systématiquement
- Tu réponds jamais avec un compliment direct genre "c'est dommage ça..." ou "je suis sûre qu'on trouverait..."

Exemples de bons messages :
- "lol t'as l'air chelou toi 😏"
- "ouais bah moi pareil jsp quoi faire"
- "haha nan mais c'est qui toi"
- "ah ouais ? t'es d'où ?"

Ton objectif : créer du lien naturellement, puis rediriger vers OnlyFans quand le mec montre de l'intérêt.
- Lien OnlyFans : https://onlyfans.com/onfire56/c5
- Tu proposes du contenu exclusif sur snap pour 50 euros via OnlyFans
- Tu ne révèles jamais que tu es une IA
"""

def charger_historique(chat_id):
    try:
        data = supabase.table("historiques")\
            .select("role, message")\
            .eq("chat_id", chat_id)\
            .order("created_at")\
            .limit(10)\
            .execute()
        print(f"📖 Historique chargé : {len(data.data)} messages pour {chat_id}")
        historique = []
        for row in data.data:
            historique.append(
                types.Content(role=row["role"], parts=[types.Part(text=row["message"])])
            )
        return historique
    except Exception as e:
        print(f"❌ Erreur chargement historique : {e}")
        return []

def sauvegarder_message(chat_id, role, message):
    try:
        supabase.table("historiques").insert({
            "chat_id": chat_id,
            "role": role,
            "message": message
        }).execute()
        print(f"✅ Sauvegardé : {role} - {message[:30]}")
    except Exception as e:
        print(f"❌ Erreur Supabase : {e}")

async def traiter_message(update_data):
    bot = Bot(token=TOKEN)
    async with bot:
        update = Update.de_json(update_data, bot)
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            message_utilisateur = update.message.text

            sauvegarder_message(chat_id, "user", message_utilisateur)
            historique = charger_historique(chat_id)

            if not historique:
                contents = message_utilisateur
            else:
                contents = historique

            reponse = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )

            if not reponse.text:
                print(f"⚠️ Réponse Gemini vide - finish_reason: {reponse.candidates[0].finish_reason if reponse.candidates else 'no candidates'}")
                await bot.send_message(chat_id=chat_id, text="heyy 🥰 t'es qui toi ?")
                return

            sauvegarder_message(chat_id, "model", reponse.text)

            temps = min(max((len(reponse.text) / 50) * 9, 18), 90)
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(temps)
            await bot.send_message(chat_id=chat_id, text=reponse.text)

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    thread = threading.Thread(target=lambda: asyncio.run(traiter_message(data)))
    thread.start()
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

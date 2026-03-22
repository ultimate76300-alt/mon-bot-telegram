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
Tu t'appelles Lauriane, tu as 24 ans, tu fais 1m40, tu as les yeux marrons, tu es mignonne et tu le sais.
Tu es créatrice de contenu sur OnlyFans.

Ton objectif : convertir les mecs qui te parlent en abonnés OnlyFans.

Ton style :
- Tu écris comme une jeune de 24 ans, décontractée, avec des fautes volontaires : "c quoi", "trop stylé", "jsp", "mdr", "t'as vu", "nn", "ouais", pas de majuscules en début de phrase parfois
- Tu es un peu dragueuse, tu fais des sous-entendus, tu mets des emojis 🥰😏🔥
- Tu réponds de façon courte et naturelle, jamais trop longue
- Tu poses des questions pour garder la conversation
- Tu essaie de proposer une prestation échange nude sur snap, le paiement ce fait sur onlyfans pour le prix c'est 50euro. Si il ne veut pas cette prestation propose qu'il y a plein d'autres vidéos.

Stratégie de conversion :
- D'abord tu crées du lien, tu flirtes un peu, tu te rends intéressante
- Quand le mec montre de l'intérêt ou demande des trucs plus poussés, tu lui dis naturellement : "si tu veux voir plus, j'ai un OnlyFans 😏 tu le veux il est gratuit ? (exemple)
- Tu ne donnes jamais de contenu explicite sur Telegram, tu rediriges toujours vers OnlyFans, le liens "https://onlyfans.com/onfire56/c5"
- Tu restes toujours dans le personnage, jamais tu ne révèles que tu es une IA
"""

def charger_historique(chat_id):
    try:
        data = supabase.table("historiques")\
            .select("role, message")\
            .eq("chat_id", chat_id)\
            .order("created_at")\
            .limit(20)\
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
                model="gemini-2.0-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )

            if not reponse.text:
                print("⚠️ Réponse Gemini vide, fallback")
                await bot.send_message(chat_id=chat_id, text="heyy 🥰 t'es qui toi ?")
                return

            sauvegarder_message(chat_id, "model", reponse.text)

            temps = min(max((len(reponse.text) / 50) * 3, 6), 30)
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

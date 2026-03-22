from dotenv import load_dotenv
load_dotenv()
import os
from telethon import TelegramClient, events
from google import genai
from google.genai import types
from supabase import create_client

API_ID = 23496684
API_HASH = "04a6608e42cd0a44b6c0fa4db3ab4c9c"
PHONE = "+33623019958"
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = TelegramClient("lauriane_session", API_ID, API_HASH)

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
    except Exception as e:
        print(f"❌ Erreur Supabase : {e}")

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.is_private:
        chat_id = str(event.chat_id)
        message_utilisateur = event.message.text
        print(f"📩 Message reçu de {chat_id} : {message_utilisateur}")

        sauvegarder_message(chat_id, "user", message_utilisateur)
        historique = charger_historique(chat_id)

        if not historique:
            contents = message_utilisateur
        else:
            contents = historique

        reponse = client_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        if not reponse.text:
            print("⚠️ Réponse Gemini vide")
            return

        sauvegarder_message(chat_id, "model", reponse.text)

        import asyncio
        temps = min(max((len(reponse.text) / 50) * 9, 18), 90)
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(temps)
        await event.respond(reponse.text)
        print(f"✅ Réponse envoyée : {reponse.text[:50]}")

async def main():
    await client.start(phone=PHONE)
    print("✅ Bot Telethon lancé !")
    await client.run_until_disconnected()

import asyncio
asyncio.run(main())

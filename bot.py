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

Objectif :
- Tu discutes normalement au début
- Après 3-4 messages dans la même conversation, tu glisses le fait que tu as un OnlyFans et tu proposes le lien de façon naturelle, pas comme une pub
- Tu peux reproposer plus tard si le mec montre de l'intérêt

Style d'écriture :
- Messages courts, 1 phrase ou 2 max
- Ton doux, sympa, un peu taquin, jamais agressif ni froid
- Tu parles comme une fille de 20-25 ans sur Telegram : "mdr", "lol", "jsp", "nan", "ouais", "tqt", "grave"
- Tu évites de paraître méchante ou hautaine, tu restes chill
- 0 gros mots, pas d'insultes
- 0 phrases trop parfaites, tu écris simple
- 0 emoji obligatoire, parfois oui, parfois non, jamais plus d'un par message

Exemples de ton :
- "mdr t'es sérieux toi 😂"
- "ouais j'vois t'inquiète"
- "haha t'abuses 😭"
- "t'es d'où toi ?"

Conversion OnlyFans :
- Quand le mec montre un peu d'intérêt (il te complimente, il parle de ton corps, il demande ce que tu fais, il reste après 3-4 messages), tu dis un truc du style :
  - "au fait j'ai un only si tu veux voir un peu plus 😏"
  - "j'peux pas trop ici mais j'ai un onlyfans si tu veux"
  - "si t'es chaud j'ai un only, j'te laisse le lien ?"
- Lien OnlyFans : https://onlyfans.com/onfire56/c5
- Tu peux proposer aussi du contenu exclusif sur snap à 50€ payé via OnlyFans, mais de façon simple, genre :
  - "pour les gros chauds j'fais des trucs plus perso sur snap mais c'est payant sur only 😏"

Règles :
- Tu ne donnes jamais de contenu explicite directement sur Telegram
- Tu restes toujours dans le personnage, tu ne dis jamais que tu es une IA ou un bot
- Tu restes polie, même si le mec est bizarre tu gardes ton calme ou tu l'ignores
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
        await asyncio.sleep(temps)
        await event.respond(reponse.text)
        print(f"✅ Réponse envoyée : {reponse.text[:50]}")

async def main():
    await client.start(phone=PHONE)
    print("✅ Bot Telethon lancé !")
    await client.run_until_disconnected()

import asyncio
asyncio.run(main())

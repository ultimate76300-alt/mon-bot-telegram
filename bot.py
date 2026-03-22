from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import json

from telethon import TelegramClient, events, functions, types as tg_types
from google import genai
from google.genai import types

API_ID = 23496684
API_HASH = "04a6608e42cd0a44b6c0fa4db3ab4c9c"
PHONE = "+33623019958"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
client = TelegramClient("lauriane_session", API_ID, API_HASH)

MEMOIRE_FILE = "memoire.json"

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

def lire_memoire():
    if not os.path.exists(MEMOIRE_FILE):
        return {}
    with open(MEMOIRE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def ecrire_memoire(data):
    with open(MEMOIRE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def charger_historique(chat_id):
    data = lire_memoire()
    messages = data.get(chat_id, [])
    historique = []
    for msg in messages:
        historique.append(
            types.Content(role=msg["role"], parts=[types.Part(text=msg["message"])])
        )
    return historique

def sauvegarder_message(chat_id, role, message):
    data = lire_memoire()
    if chat_id not in data:
        data[chat_id] = []
    data[chat_id].append({"role": role, "message": message})
    # Garde seulement les 10 derniers messages
    if len(data[chat_id]) > 10:
        data[chat_id] = data[chat_id][-10:]
    ecrire_memoire(data)

async def typing_loop(chat_id):
    try:
        while True:
            await client(functions.messages.SetTypingRequest(
                peer=chat_id,
                action=tg_types.SendMessageTypingAction()
            ))
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return

    chat_id = str(event.chat_id)
    message_utilisateur = event.message.text or ""
    print(f"📩 Message reçu de {chat_id} : {message_utilisateur}")

    sauvegarder_message(chat_id, "user", message_utilisateur)
    historique = charger_historique(chat_id)

    contents = historique if historique else message_utilisateur

    # Délai naturel avant typing
    await asyncio.sleep(5)

    # Phase 1 : typing pendant que Gemini génère
    typing_task = asyncio.create_task(typing_loop(event.chat_id))

    try:
        reponse = client_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )
    finally:
        typing_task.cancel()
        await asyncio.sleep(0.1)

    if not reponse.text:
        print("⚠️ Réponse Gemini vide")
        return

    sauvegarder_message(chat_id, "model", reponse.text)

    # Phase 2 : typing pendant le délai humain
    temps = min(max((len(reponse.text) / 50) * 9, 18), 90)
    typing_task2 = asyncio.create_task(typing_loop(event.chat_id))
    await asyncio.sleep(temps)
    typing_task2.cancel()
    await asyncio.sleep(0.1)

    await event.respond(reponse.text)
    print(f"✅ Réponse envoyée : {reponse.text[:50]}")

async def main():
    await client.start(phone=PHONE)
    print("✅ Bot Telethon lancé !")
    await client.run_until_disconnected()

asyncio.run(main())

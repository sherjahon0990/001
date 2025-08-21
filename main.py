import logging
import requests
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

# 🔑 Telegram token va OpenRouter API kaliti
TELEGRAM_TOKEN = "8369312930:AAF0ot1L_AVjmYN9yXqoFSOO3INh3bQzvCY"  # Tokenni o'zing qo'y
OPENROUTER_API_KEY = "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"
ADMIN_ID = 7722612272  # O'zingning Telegram ID

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# 🔹 Chat tarixini saqlash
CHAT_HISTORY_FILE = "chat_history.json"
if os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
        chat_history = json.load(f)
else:
    chat_history = {}

# 🔹 Foydalanuvchi tilini saqlash
user_language_map = {}

def detect_language(user_id: str, text: str):
    text_lower = text.lower()
    if "inglizcha gapir" in text_lower:
        user_language_map[user_id] = "en"
        return "en"
    elif "ruscha gapir" in text_lower:
        user_language_map[user_id] = "ru"
        return "ru"
    return user_language_map.get(user_id, "uz")

# 🔹 OpenRouter orqali AI javobi
def ask_ai(prompt: str, language: str = "uz") -> str:
    final_prompt = f"Siz foydalanuvchiga {language} tilida ANIQ va FACTUAL javob berasiz. Savol: {prompt}"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": final_prompt}],
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ AI javob bera olmadi. Server xatosi ({response.status_code})"
    except Exception as e:
        return f"❌ AI javob bera olmadi: {e}"

# 🔹 Chatni saqlash
def save_chat(user_id: str, user_text: str, ai_text: str, language: str):
    user_chats = chat_history.get(user_id, [])
    chat_entry = {"user": user_text, "ai": ai_text, "lang": language}
    user_chats.append(chat_entry)
    chat_history[user_id] = user_chats
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=2)

# 🔹 /start komandasi
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 Salom! Men ChatGPT kabi AI botman.\n"
        "Savollaringizni yozing.\n"
        "Tilni o‘zgartirish: Inglizcha gapir, Ruscha gapir va hokazo.\n"
        "📜 /history — chat tarixini ko‘rish\n"
        "📢 /broadcast — admin xabar yuborish (faqat admin)"
    )

# 🔹 /history komandasi
@dp.message(Command("history"))
async def show_history(message: Message):
    user_id = str(message.from_user.id)
    user_chats = chat_history.get(user_id, [])
    if not user_chats:
        await message.answer("Sizda hali chatlar mavjud emas.")
        return
    text = ""
    for idx, chat in enumerate(user_chats):
        text += f"{idx+1}. Siz: {chat['user']}\n🤖 Bot: {chat['ai']}\n\n"
    await message.answer(text)

# 🔹 /broadcast komandasi — faqat admin
@dp.message(Command("broadcast"))
async def broadcast_message(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz!")
        return
    text = message.text[len("/broadcast "):].strip()
    if not text:
        await message.answer("❌ Iltimos, xabar matnini kiriting.")
        return
    for user_id in chat_history.keys():
        try:
            await bot.send_message(user_id, f"📢 Admin xabari:\n{text}")
        except Exception as e:
            logging.error(f"Xatolik {user_id}: {e}")
    await message.answer("✅ Xabar barcha foydalanuvchilarga yuborildi.")

# 🔹 Har qanday xabarni AI ga yuborish
@dp.message()
async def chat_message(message: Message):
    user_id = str(message.from_user.id)
    user_text = message.text
    language = detect_language(user_id, user_text)

    await message.answer("⌛️ Javob tayyorlanmoqda...")
    loop = asyncio.get_event_loop()
    ai_reply = await loop.run_in_executor(None, ask_ai, user_text, language)
    await message.answer(ai_reply)
    save_chat(user_id, user_text, ai_reply, language)

# 🔹 Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

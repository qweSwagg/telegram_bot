import asyncio
import os
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("TOKEN")

OWNER_ID = 7548603865

ADMIN_CHAT_ID = -1003850339565

POINT_THREAD = 685
WARN_THREAD = 865
SHOP_THREAD = 952

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

users = {}

# =========================
# ПРОВЕРКА АДМИНА
# =========================

async def is_admin(user_id):
    admins = await bot.get_chat_administrators(ADMIN_CHAT_ID)
    return user_id in [a.user.id for a in admins]

# =========================
# РАНДОМ ЭМОДЗИ
# =========================

def emoji():
    return random.choice(["🎉","🎁","✨","🥳","🎊"])

# =========================
# БАЛЛЫ
# =========================

@dp.message(F.text.startswith("#баллы"))
async def add_points(message: Message):

    if message.chat.id != ADMIN_CHAT_ID:
        return

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    if len(parts) < 3:
        return

    try:
        amount = int(parts[-1])
    except:
        return

    target = message.reply_to_message.from_user if message.reply_to_message else None

    if not target:
        return await message.answer("Ответь на сообщение пользователя")

    users.setdefault(target.id, {"points":0})

    users[target.id]["points"] += amount

    await message.answer(
        f"{emoji()} {target.mention_html()}\n"
        f"Твои баллы: {users[target.id]['points']}"
    )

# =========================
# МОИ БАЛЛЫ
# =========================

@dp.message(F.text == "!мои баллы")
async def my_points(message: Message):

    if message.chat.id != ADMIN_CHAT_ID:
        return

    data = users.get(message.from_user.id, {"points":0})

    await message.answer(
        f"🏦 Банк\n"
        f"💰 Баллы: {data['points']}"
    )

# =========================
# МАГАЗИН
# =========================

@dp.message(F.text == "!магазин")
async def shop(message: Message):

    if message.message_thread_id != SHOP_THREAD:
        return

    await message.answer(
        "🛒 Магазин\n\n"
        "🌴 Отгул — 15 баллов\n"
        "🎯 Снять выговор — 30 баллов\n\n"
        "!купить отгул\n"
        "!купить выговор"
    )

# =========================
# РЕЙТИНГ
# =========================

@dp.message(F.text == "!рейтинг")
async def rating(message: Message):

    if message.chat.id != ADMIN_CHAT_ID:
        return

    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1]["points"],
        reverse=True
    )

    text = "🏆 Рейтинг\n\n"

    for i,(uid,data) in enumerate(sorted_users[:10],1):

        try:
            member = await bot.get_chat_member(ADMIN_CHAT_ID, uid)

            place = ""
            if i == 1:
                place = "Самый лучший!"
            elif i == 2:
                place = "Ты почти лучший!"
            elif i == 3:
                place = "Работай усерднее!"

            text += f"{i}. {member.user.first_name} — {data['points']} {place}\n"

        except:
            pass

    await message.answer(text)

# =========================
# ЗАПУСК
# =========================

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
import asyncio
import random
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ======================
# НАСТРОЙКИ
# ======================

TOKEN = os.getenv("TOKEN")

OWNER_ID = 7548603865

ADMIN_CHAT_ID = -1003850339565

POINT_THREAD_ID = 685
WARN_THREAD_ID = 865
SHOP_THREAD_ID = 952

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

users = {}
activity = {}

# ======================
# АДМИН ПРОВЕРКА
# ======================

async def is_admin(user_id):
    try:
        admins = await bot.get_chat_administrators(ADMIN_CHAT_ID)
        return user_id in [a.user.id for a in admins]
    except:
        return False

# ======================
# ПОИСК ПОЛЬЗОВАТЕЛЯ
# ======================

async def find_user(message: Message):

    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()
    if len(parts) < 2:
        return None

    username = parts[1].replace("@","")

    try:
        member = await bot.get_chat_member(ADMIN_CHAT_ID, username)
        return member.user
    except:
        return None

# ======================
# ЭМОДЗИ
# ======================

def emoji():
    return random.choice([
        "🎉","🎁","✨","🥳","🎊"
    ])

# ======================
# БАЛЛЫ
# ======================

@dp.message(F.text.lower().startswith("#баллы"))
async def give_points(message: Message):

    if message.chat.id != ADMIN_CHAT_ID:
        return

    if message.message_thread_id != POINT_THREAD_ID:
        return

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    try:
        amount = int(parts[-1])
    except:
        return

    target = await find_user(message)
    if not target:
        return await message.answer("Пользователь не найден")

    users.setdefault(target.id,{"points":0,"warns":0})

    users[target.id]["points"] += amount

    await message.answer(
        f"{emoji()} {target.mention_html()}\n"
        f"Твои баллы: {users[target.id]['points']}"
    )

# ======================
# МОИ БАЛЛЫ
# ======================

@dp.message(F.text == "!мои баллы")
async def my_points(message: Message):

    data = users.get(message.from_user.id,{"points":0})

    await message.answer(
        f"🏦 Личный банк\n"
        f"💰 Баллы: {data['points']}"
    )

# ======================
# ВЫГОВОРЫ
# ======================

@dp.message(F.text.lower().startswith("#выговор"))
async def warn_user(message: Message):

    if message.chat.id != ADMIN_CHAT_ID:
        return

    if message.message_thread_id != WARN_THREAD_ID:
        return

    if not await is_admin(message.from_user.id):
        return

    if not message.reply_to_message:
        return await message.answer("Ответь на пользователя")

    parts = message.text.split("\n")

    if len(parts) < 2:
        return await message.answer("Причину напиши с новой строки")

    reason = parts[1]

    target = message.reply_to_message.from_user

    users.setdefault(target.id,{"points":0,"warns":0})

    users[target.id]["warns"] += 1

    await bot.send_message(
        WARN_THREAD_ID,
        f"⚠ Выговор {users[target.id]['warns']}/3\n"
        f"👤 {target.mention_html()}\n"
        f"👮 Выдал: {message.from_user.mention_html()}\n"
        f"📝 Причина:\n{reason}"
    )

# ======================
# МАГАЗИН
# ======================

@dp.message(F.text == "!магазин")
async def shop(message: Message):

    if message.message_thread_id != SHOP_THREAD_ID:
        return

    await message.answer(
        "🛒 Магазин\n\n"
        "🌴 Отгул — 15 баллов\n"
        "🎯 Снять выговор — 30 баллов\n\n"
        "!купить отгул\n"
        "!купить выговор"
    )

# ======================
# ПРОВЕРКА ОТГУЛОВ
# ======================

async def check_vacations():

    while True:

        now = datetime.now()

        for uid,data in users.items():

            if not data.get("vacation"):
                continue

            if data["vacation"] <= now:

                member = await bot.get_chat_member(ADMIN_CHAT_ID, uid)

                await bot.send_message(
                    ADMIN_CHAT_ID,
                    f"⏰ {member.user.mention_html()} Отгул окончен"
                )

                data["vacation"] = None

        await asyncio.sleep(60)

# ======================
# ЗАПУСК
# ======================

async def main():
    asyncio.create_task(check_vacations())
    await dp.start_polling(bot)

asyncio.run(main())
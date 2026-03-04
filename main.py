import asyncio
import random
from datetime import datetime, timedelta
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ======================
# НАСТРОЙКИ
# ======================

TOKEN = os.getenv("TOKEN")

OWNER_ID = 123456789

WORK_CHAT_ID = -1003793311517
ADMIN_ROLE_CHAT_ID = -1003850339565
WARN_THREAD_ID = 865
SHOP_THREAD_ID = 952

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

users = {}
activity = {}
warn_messages = {}

# ======================
# ПРОВЕРКА АДМИНА
# ======================

async def is_admin(user_id, chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
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
        member = await bot.get_chat_member(WORK_CHAT_ID, username)
        return member.user
    except:
        return None

# ======================
# РАНДОМ ЭМОДЗИ
# ======================

def emoji():
    return random.choice(["🎉","🎊","🎁","✨","🥳"])

# ======================
# БАЛЛЫ
# ======================

@dp.message(F.text.startswith("#баллы"))
async def give_points(message: Message):

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

    users.setdefault(target.id,{
        "points":0,
        "warns":0,
        "vacation":None,
        "vacation_warned":False
    })

    users[target.id]["points"] += amount

    await message.answer(
        f"{emoji()} {target.mention_html()}\n"
        f"Твои баллы {amount} добавлены в твой личный банк!"
    )

# ======================
# МОИ БАЛЛЫ
# ======================

@dp.message(F.text == "!мои баллы")
async def my_points(message: Message):

    data = users.get(message.from_user.id,{"points":0})

    await message.answer(
        f"🏦 Личный банк\n"
        f"💰 {message.from_user.mention_html()}\n"
        f"Баллы: {data['points']}"
    )

# ======================
# АКТИВНОСТЬ
# ======================

@dp.message()
async def track_activity(message: Message):

    if message.chat.id != WORK_CHAT_ID:
        return

    if not await is_admin(message.from_user.id, WORK_CHAT_ID):
        return

    uid = message.from_user.id
    now = datetime.now()

    activity.setdefault(uid,{"messages":[],"last_active":None})

    activity[uid]["messages"].append(now)
    activity[uid]["last_active"] = now

    activity[uid]["messages"] = [
        t for t in activity[uid]["messages"]
        if now - t <= timedelta(days=1)
    ]

# ======================
# ПОСМОТРЕТЬ АКТИВНОСТЬ
# ======================

@dp.message(F.text.startswith("!посмотреть активность"))
async def check_activity(message: Message):

    if message.chat.id != WORK_CHAT_ID:
        return

    if not await is_admin(message.from_user.id, WORK_CHAT_ID):
        return

    target = await find_user(message)
    if not target:
        return await message.answer("Пользователь не найден")

    if not await is_admin(target.id, WORK_CHAT_ID):
        return await message.answer("Можно смотреть только админов")

    data = activity.get(target.id)

    if not data:
        return await message.answer("Нет активности")

    now = datetime.now()

    msgs = [t for t in data["messages"] if now - t <= timedelta(days=1)]

    last = data["last_active"]
    last_text = last.strftime("%d.%m.%Y %H:%M") if last else "нет данных"

    await message.answer(
        f"{target.mention_html()}\n"
        f"📊 За 24ч: {len(msgs)} сообщений\n"
        f"🕒 Последний актив: {last_text}"
    )

# ======================
# МАГАЗИН
# ======================

@dp.message(F.text == "!магазин")
async def shop(message: Message):

    if message.message_thread_id != SHOP_THREAD_ID:
        return

    await message.answer(
        "🛒 Магазин\n"
        "🌴 Отгул — 15 баллов\n"
        "🎯 Снять выговор — 30 баллов\n\n"
        "!купить отгул\n"
        "!купить выговор"
    )

# ======================
# ПОКУПКИ
# ======================

@dp.message(F.text.startswith("!купить"))
async def buy(message: Message):

    if message.message_thread_id != SHOP_THREAD_ID:
        return

    data = users.get(message.from_user.id)
    if not data:
        return

    text = message.text.lower()

    # Отгул
    if "отгул" in text:

        if data["points"] < 15:
            return await message.answer("Недостаточно баллов")

        data["points"] -= 15

        now = datetime.now()

        if not data["vacation"] or data["vacation"] < now:
            data["vacation"] = now + timedelta(days=1)
        else:
            data["vacation"] += timedelta(days=1)

        await message.answer(
            f"🌴 Отгул до {data['vacation'].strftime('%d.%m.%Y %H:%M')}"
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

            remaining = data["vacation"] - now

            if remaining.total_seconds() <= 3600 and not data.get("vacation_warned"):

                member = await bot.get_chat_member(WORK_CHAT_ID, uid)

                await bot.send_message(
                    WORK_CHAT_ID,
                    f"🔔 {member.user.mention_html()} 1 час до конца отгула"
                )

                data["vacation_warned"] = True

            if data["vacation"] <= now:

                member = await bot.get_chat_member(WORK_CHAT_ID, uid)

                await bot.send_message(
                    WORK_CHAT_ID,
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
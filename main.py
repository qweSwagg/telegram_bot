import asyncio
import random
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("TOKEN")

OWNER_ID = 123456789

MAIN_CHAT_ID = -1003850339565
WARN_THREAD_ID = 865
SHOP_THREAD_ID = 952

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

users = {}
warn_messages = {}

# =========================
# ЭМОДЗИ
# =========================

def random_emoji():
    return random.choice(["🎉","🎊","🎁","✨","🥳"])

# =========================
# ПОИСК ПОЛЬЗОВАТЕЛЯ
# =========================

async def get_target_user(message: Message):

    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    if len(parts) < 2:
        return None

    username = parts[1].replace("@","")

    try:
        member = await bot.get_chat_member(MAIN_CHAT_ID, username)
        return member.user
    except:
        return None

# =========================
# БАЛЛЫ
# =========================

@dp.message(F.text.lower().startswith("#баллы"))
async def give_points(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    try:
        amount = int(parts[-1])
    except:
        return await message.answer("Укажи количество баллов")

    target = await get_target_user(message)

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
        f"{random_emoji()}\n"
        f"{target.full_name}\n"
        f"Баллы начислены: {amount}"
    )

# =========================
# МОИ БАЛЛЫ
# =========================

@dp.message(F.text == "!мои баллы")
async def my_points(message: Message):

    data = users.get(message.from_user.id,{"points":0})

    await message.answer(
        f"🏦 Личный банк\n"
        f"💰 Баллы: {data['points']}"
    )

# =========================
# ВЫГОВОР
# =========================

@dp.message(F.text.lower().startswith("#выговор"))
async def warn_user(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message:
        return await message.answer("Ответь на пользователя")

    parts = message.text.split("\n")

    if len(parts) < 2:
        return await message.answer("Причину напиши с новой строки")

    reason = parts[1]

    target = message.reply_to_message.from_user

    users.setdefault(target.id,{
        "points":0,
        "warns":0,
        "vacation":None
    })

    users[target.id]["warns"] += 1

    warns = users[target.id]["warns"]

    if warns == 1:
        status = "⚠ Выговор 1/3 Будь осторожнее"
    elif warns == 2:
        status = "⚠ Выговор 2/3"
    else:
        status = "⚠ Выговор 3/3\nЖаль, но вы будете разжалованы."

    text = (
        "━━━━━━━━━━━━━━━\n"
        f"{status}\n"
        f"👤 {target.full_name}\n"
        f"👮 Выдал: {message.from_user.full_name}\n"
        f"📝 Причина:\n{reason}\n"
        "━━━━━━━━━━━━━━━"
    )

    sent = await bot.send_message(
        MAIN_CHAT_ID,
        text,
        message_thread_id=WARN_THREAD_ID
    )

    warn_messages[target.id] = sent.message_id

# =========================
# МАГАЗИН
# =========================

@dp.message(F.text == "!магазин")
async def shop(message: Message):

    if message.message_thread_id != SHOP_THREAD_ID:
        return

    await message.answer(
        "🛒 Магазин\n\n"
        "🌴 Отгул — 15 баллов\n"
        "🎯 Снять выговор — 30 баллов\n"
        "!купить отгул\n"
        "!купить выговор"
    )

# =========================
# ПОКУПКИ
# =========================

@dp.message(F.text.lower().startswith("!купить"))
async def buy(message: Message):

    if message.message_thread_id != SHOP_THREAD_ID:
        return

    user = message.from_user
    data = users.get(user.id)

    if not data:
        return await message.answer("Нет баллов")

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

    # Снятие выговора
    elif "выговор" in text:

        if data["points"] < 30:
            return await message.answer("Недостаточно баллов")

        if data["warns"] <= 0:
            return await message.answer("Нет выговоров")

        data["points"] -= 30
        data["warns"] -= 1

        if user.id in warn_messages:
            try:
                await bot.delete_message(
                    MAIN_CHAT_ID,
                    warn_messages[user.id]
                )
            except:
                pass

        await message.answer(
            f"✅ Выговор снят\n"
            f"Осталось: {data['warns']}/3"
        )

# =========================
# РЕЙТИНГ
# =========================

@dp.message(F.text == "!рейтинг")
async def rating(message: Message):

    if not users:
        return await message.answer("Нет данных")

    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1]["points"],
        reverse=True
    )

    text = "🏆 Рейтинг\n\n"

    medals = ["🥇","🥈","🥉"]

    for i,(uid,data) in enumerate(sorted_users[:10]):

        try:
            member = await bot.get_chat_member(MAIN_CHAT_ID, uid)
            name = member.user.full_name
        except:
            name = f"ID {uid}"

        extra = ""
        if i == 0:
            extra = "Самый лучший!"
        elif i == 1:
            extra = "Ты почти лучший!"
        elif i == 2:
            extra = "Работай усерднее!"

        medal = medals[i] if i < 3 else "🔹"

        text += f"{medal} {name} — {data['points']} {extra}\n"

    await message.answer(text)

# =========================
# ЗАПУСК
# =========================

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
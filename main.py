import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode

TOKEN = "YOUR_BOT_TOKEN"
MAIN_CHAT_ID = -1003850339565
WARN_THREAD_ID = 865
SHOP_THREAD_ID = 952

# 👑 ВЛАДЕЛЕЦ + АДМИНЫ
OWNER_ID = 123456789
ADMINS = [OWNER_ID]  # сюда добавляй id админов

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

users = {}
warn_messages = {}

# 🎉 Рандомные праздничные эмодзи
def random_emoji():
    return random.choice(["🎉", "🎊", "🎈", "✨", "🥳", "🎆", "🪩"])

# 🔎 Универсальный поиск пользователя
async def get_target_user(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()
    if len(parts) < 2:
        return None

    target_raw = parts[1].replace("@", "")

    # если ID
    if target_raw.isdigit():
        try:
            member = await bot.get_chat_member(MAIN_CHAT_ID, int(target_raw))
            return member.user
        except:
            return None

    # если username
    try:
        member = await bot.get_chat_member(MAIN_CHAT_ID, target_raw)
        return member.user
    except:
        return None


# =========================
# 💰 НАЧИСЛЕНИЕ БАЛЛОВ
# =========================
@dp.message(F.text.startswith("#баллы"))
async def give_points(message: Message):
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Пример: #баллы @user 10")

    try:
        amount = int(parts[-1])
    except:
        return await message.answer("Укажи количество баллов")

    target = await get_target_user(message)
    if not target:
        return await message.answer("❌ Пользователь не найден")

    users.setdefault(target.id, {
        "points": 0,
        "warns": 0,
        "vacation": None,
        "vacation_warned": False
    })

    users[target.id]["points"] += amount
    emoji = random_emoji()

    await message.answer(emoji)
    await message.answer(
        f"{target.mention_html()}\n"
        f"Вам начислено <b>{amount}</b> баллов!\n"
        f"Поздравляем! {emoji}"
    )


# =========================
# 🏦 МОИ БАЛЛЫ
# =========================
@dp.message(F.text == "!мои баллы")
async def my_points(message: Message):
    data = users.get(message.from_user.id, {"points": 0})

    await message.answer(
        f"🏦 <b>Это ваш личный банк</b>\n\n"
        f"👤 {message.from_user.mention_html()}\n"
        f"💰 У вас <b>{data['points']}</b> баллов"
    )


# =========================
# 🌴 МОЙ ОТГУЛ
# =========================
@dp.message(F.text == "!мой отгул")
async def my_vacation(message: Message):
    data = users.get(message.from_user.id)

    if not data or not data.get("vacation"):
        return await message.answer("🌴 У вас нет активного отгула.")

    now = datetime.now()
    vacation_end = data["vacation"]

    if vacation_end <= now:
        data["vacation"] = None
        return await message.answer("🌴 Ваш отгул уже закончился.")

    remaining = vacation_end - now
    hours = remaining.days * 24 + remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60

    await message.answer(
        f"🌴 <b>Отгул активен</b>\n\n"
        f"⏳ Осталось: {hours} ч. {minutes} мин.\n"
        f"📅 До: {vacation_end.strftime('%d.%m.%Y %H:%M')}"
    )


# =========================
# 👑 !отгулы (АДМИНЫ)
# =========================
@dp.message(F.text == "!отгулы")
async def active_vacations(message: Message):
    if message.from_user.id not in ADMINS:
        return

    now = datetime.now()
    text = "🌴 <b>Сейчас отдыхают:</b>\n\n"
    found = False

    for user_id, data in users.items():
        if data.get("vacation") and data["vacation"] > now:
            member = await bot.get_chat_member(MAIN_CHAT_ID, user_id)
            remaining = data["vacation"] - now
            hours = remaining.days * 24 + remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60

            text += (
                f"{member.user.mention_html()}\n"
                f"⏳ {hours} ч. {minutes} мин.\n\n"
            )
            found = True

    if not found:
        text = "🌴 Сейчас никто не отдыхает."

    await message.answer(text)


# =========================
# 🛒 МАГАЗИН (только ветка 952)
# =========================
@dp.message(F.text == "!магазин")
async def shop(message: Message):
    if message.message_thread_id != SHOP_THREAD_ID:
        return

    await message.answer(
        "🛒 <b>Магазин</b>\n\n"
        "🎯 Снять выговор — 30 баллов\n"
        "🌴 Отгул — 15 баллов"
    )


# =========================
# 🛍 ПОКУПКА
# =========================
@dp.message(F.text.startswith("!купить"))
async def buy(message: Message):
    if message.message_thread_id != SHOP_THREAD_ID:
        return

    user = message.from_user
    data = users.get(user.id)

    if not data:
        return await message.answer("У вас нет баллов.")

    text = message.text.lower()

    # 🌴 Отгул
    if "отгул" in text:
        if data["points"] < 15:
            return await message.answer("Недостаточно баллов.")

        data["points"] -= 15
        now = datetime.now()

        if not data["vacation"] or data["vacation"] < now:
            data["vacation"] = now + timedelta(days=1)
        else:
            data["vacation"] += timedelta(days=1)

        data["vacation_warned"] = False

        await message.answer(
            f"🌴 Отгул активен до {data['vacation'].strftime('%d.%m.%Y %H:%M')}"
        )

    # 🎯 Снять выговор
    elif "выговор" in text:
        if data["points"] < 30:
            return await message.answer("Недостаточно баллов.")
        if data["warns"] <= 0:
            return await message.answer("У вас нет выговоров.")

        data["points"] -= 30
        data["warns"] -= 1

        if user.id in warn_messages:
            try:
                await bot.delete_message(MAIN_CHAT_ID, warn_messages[user.id])
            except:
                pass

        await message.answer(
            f"✅ Выговор снят\n"
            f"📊 Осталось: {data['warns']}/3"
        )


# =========================
# ⏰ ФОНОВАЯ ПРОВЕРКА ОТГУЛОВ
# =========================
async def check_vacations():
    while True:
        now = datetime.now()

        for user_id, data in users.items():
            if not data.get("vacation"):
                continue

            remaining = data["vacation"] - now

            # 🔔 за 1 час
            if (
                remaining.total_seconds() <= 3600
                and remaining.total_seconds() > 0
                and not data.get("vacation_warned")
            ):
                member = await bot.get_chat_member(MAIN_CHAT_ID, user_id)
                await bot.send_message(
                    MAIN_CHAT_ID,
                    f"🔔 {member.user.mention_html()}\n"
                    f"До окончания отгула остался 1 час!"
                )
                data["vacation_warned"] = True

            # ⏰ окончание
            if data["vacation"] <= now:
                member = await bot.get_chat_member(MAIN_CHAT_ID, user_id)
                await bot.send_message(
                    MAIN_CHAT_ID,
                    f"⏰ {member.user.mention_html()}\n"
                    f"Ваш отгул окончен, приступайте к работе!"
                )
                data["vacation"] = None
                data["vacation_warned"] = False

        await asyncio.sleep(60)


# =========================
# 🚀 ЗАПУСК
# =========================
async def main():
    asyncio.create_task(check_vacations())
    await dp.start_polling(bot)

asyncio.run(main())
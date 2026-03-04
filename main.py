import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = "YOUR_BOT_TOKEN"

OWNER_ID = 123456789

WORK_CHAT_ID = -1003793311517      # Чат где считается активность
ADMIN_ROLE_CHAT_ID = -1003850339565  # Чат где выдаётся роль

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

users = {}
activity = {}
warn_messages = {}

# =========================
# РАНДОМ ЭМОДЗИ
# =========================

def random_emoji():
    return random.choice(["🎉","🎊","🎈","✨","🥳","🎁"])

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
        member = await bot.get_chat_member(WORK_CHAT_ID, username)
        return member.user
    except:
        return None

# =========================
# АКТИВНОСТЬ (ТОЛЬКО АДМИНЫ)
# =========================

@dp.message()
async def track_activity(message: Message):

    if message.chat.id != WORK_CHAT_ID:
        return

    try:
        admins = [a.user.id for a in await bot.get_chat_administrators(WORK_CHAT_ID)]
        if message.from_user.id not in admins:
            return
    except:
        return

    uid = message.from_user.id
    now = datetime.now()

    activity.setdefault(uid, {"messages": [], "last_active": None})

    activity[uid]["messages"].append(now)
    activity[uid]["last_active"] = now

    activity[uid]["messages"] = [
        t for t in activity[uid]["messages"]
        if now - t <= timedelta(days=1)
    ]

# =========================
# ПОСМОТРЕТЬ АКТИВНОСТЬ
# =========================

@dp.message(F.text.startswith("!посмотреть активность"))
async def check_activity(message: Message):

    if message.chat.id != WORK_CHAT_ID:
        return

    try:
        admins_ids = [a.user.id for a in await bot.get_chat_administrators(WORK_CHAT_ID)]
    except:
        admins_ids = []

    if message.from_user.id not in admins_ids:
        return

    target = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = message.text.split()

        if len(parts) >= 3:
            target_name = parts[2].replace("@","")

            try:
                member = await bot.get_chat_member(WORK_CHAT_ID, target_name)
                target = member.user
            except:
                pass

    if not target:
        return await message.answer("❌ Пользователь не найден")

    # Только админы
    try:
        if target.id not in admins_ids:
            return await message.answer("❌ Можно смотреть только админов")
    except:
        pass

    data = activity.get(target.id)

    if not data:
        return await message.answer(
            f"{target.mention_html()}\n"
            "📊 Сообщений за 24ч: 0\n"
            "🕒 Последний актив: нет данных"
        )

    now = datetime.now()

    msgs = [
        t for t in data["messages"]
        if now - t <= timedelta(days=1)
    ]

    last_active = data["last_active"]

    last_text = last_active.strftime("%d.%m.%Y %H:%M") if last_active else "нет данных"

    await message.answer(
        f"{target.mention_html()}\n\n"
        f"📊 Сообщений за 24ч: <b>{len(msgs)}</b>\n"
        f"🕒 Последний актив: <b>{last_text}</b>"
    )

# =========================
# БАЛЛЫ
# =========================

@dp.message(F.text.startswith("#баллы"))
async def give_points(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()
    if len(parts) < 3:
        return

    try:
        amount = int(parts[-1])
    except:
        return

    target = await get_target_user(message)
    if not target:
        return

    users.setdefault(target.id,{
        "points":0,
        "warns":0,
        "vacation":None,
        "vacation_warned":False
    })

    users[target.id]["points"] += amount

    await message.answer(
        f"{random_emoji()} {target.mention_html()}\n"
        f"Вам начислено {amount} баллов!"
    )

# =========================
# ОТГУЛЫ + РОЛЬ
# =========================

async def give_rest_role(user_id):
    try:
        await bot.promote_chat_member(
            ADMIN_ROLE_CHAT_ID,
            user_id,
            can_manage_chat=False
        )

        await bot.set_chat_administrator_custom_title(
            ADMIN_ROLE_CHAT_ID,
            user_id,
            "🌴 Отдыхает"
        )
    except:
        pass

async def remove_rest_role(user_id):
    try:
        await bot.set_chat_administrator_custom_title(
            ADMIN_ROLE_CHAT_ID,
            user_id,
            ""
        )
    except:
        pass

# =========================
# ФОНОВАЯ ПРОВЕРКА ОТГУЛОВ
# =========================

async def check_vacations():

    while True:

        now = datetime.now()

        for uid,data in users.items():

            if not data.get("vacation"):
                continue

            remaining = data["vacation"] - now

            # 1 час предупреждение
            if (
                remaining.total_seconds() <= 3600
                and remaining.total_seconds() > 0
                and not data.get("vacation_warned")
            ):
                try:
                    member = await bot.get_chat_member(WORK_CHAT_ID, uid)

                    await bot.send_message(
                        WORK_CHAT_ID,
                        f"🔔 {member.user.mention_html()}\n"
                        "До окончания отгула остался 1 час!"
                    )

                    data["vacation_warned"] = True
                except:
                    pass

            # окончание
            if data["vacation"] <= now:

                member = await bot.get_chat_member(WORK_CHAT_ID, uid)

                await remove_rest_role(uid)

                await bot.send_message(
                    WORK_CHAT_ID,
                    f"⏰ {member.user.mention_html()}\n"
                    "Ваш отгул окончен, приступайте к работе!"
                )

                data["vacation"] = None
                data["vacation_warned"] = False

        await asyncio.sleep(60)

# =========================
# ЗАПУСК
# =========================

async def main():
    asyncio.create_task(check_vacations())
    await dp.start_polling(bot)

asyncio.run(main())
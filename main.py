import telebot
import json
import re
import os
import datetime

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

OWNER_ID = 7548603865

GROUP_ID = -1003850339565
BALANCE_THREAD = 685
WARNING_THREAD = 865
SHOP_THREAD = 952

# =========================
# БАЗА
# =========================

def load_db():
    try:
        with open("scores.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)

scores = load_db()

# =========================
# ПОИСК
# =========================

def find_user(identifier):
    identifier = identifier.lower()

    for uid, data in scores.items():
        if identifier == uid:
            return uid
        if identifier in data["name"].lower():
            return uid
    return None

# =========================
# ДОБАВЛЕНИЕ БАЛЛОВ
# =========================

@bot.message_handler(func=lambda m: m.text and "#баллы" in m.text.lower())
def add_points(message):

    uid = str(message.from_user.id)
    name = message.from_user.first_name

    match = re.search(r"#баллы\s*[+]?\s*(\d+)", message.text.lower())
    if not match:
        return

    points = int(match.group(1))

    if uid not in scores:
        scores[uid] = {
            "name": name,
            "points": 0,
            "warnings": 0,
            "vacation_end": None
        }

    scores[uid]["name"] = name
    scores[uid]["points"] += points
    save_db(scores)

    bot.send_message(GROUP_ID, "🎁", message_thread_id=BALANCE_THREAD)

    bot.forward_message(
        GROUP_ID,
        message.chat.id,
        message.message_id,
        message_thread_id=BALANCE_THREAD
    )

    bot.send_message(
        GROUP_ID,
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {name}\n"
        f"🏦 Твой банк: {scores[uid]['points']} баллов\n"
        f"━━━━━━━━━━━━━━━",
        message_thread_id=BALANCE_THREAD
    )

    bot.reply_to(
        message,
        f"💰 Баллы {points} добавлены!\n"
        f"🏦 Сейчас у тебя {scores[uid]['points']} баллов"
    )

# =========================
# МОИ БАЛЛЫ
# =========================

@bot.message_handler(func=lambda m: m.text and "!мои баллы" in m.text.lower())
def my_balance(message):

    uid = str(message.from_user.id)

    if uid not in scores:
        bot.reply_to(message, "У вас пока 0 баллов")
        return

    bot.reply_to(
        message,
        f"🏦 Это ваш личный банк\n\n"
        f"💰 У вас {scores[uid]['points']} баллов"
    )

# =========================
# РЕЙТИНГ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!баллы"))
def rating(message):

    if not scores:
        bot.reply_to(message, "Нет участников")
        return

    sorted_users = sorted(
        scores.values(),
        key=lambda x: x["points"],
        reverse=True
    )

    text = "🏆 Рейтинг участников\n\n"

    for i, user in enumerate(sorted_users, 1):

        medal = "▫"
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"

        text += f"{medal} {user['name']} — {user['points']} баллов\n"

    bot.reply_to(message, text)

# =========================
# МАГАЗИН (ТОЛЬКО 952)
# =========================

@bot.message_handler(func=lambda m: m.text and "!магазин" in m.text.lower())
def shop(message):

    if message.message_thread_id != SHOP_THREAD:
        return

    bot.reply_to(
        message,
        "🛒 Магазин\n\n"
        "🎯 Снять выговор — 30 баллов\n"
        "🌴 Отгул — 15 баллов (суммируется)\n\n"
        "Команды:\n"
        "!купить выговор\n"
        "!купить отгул"
    )

# =========================
# ПОКУПКИ
# =========================

@bot.message_handler(func=lambda m: m.text and "!купить" in m.text.lower())
def buy(message):

    if message.message_thread_id != SHOP_THREAD:
        return

    uid = str(message.from_user.id)

    if uid not in scores:
        bot.reply_to(message, "❌ У тебя нет баллов")
        return

    text = message.text.lower()

    # ===== СНЯТЬ ВЫГОВОР =====
    if "выговор" in text:

        if scores[uid]["points"] < 30:
            bot.reply_to(message, "❌ Нужно 30 баллов")
            return

        scores[uid]["points"] -= 30
        scores[uid]["warnings"] = max(0, scores[uid]["warnings"] - 1)

        bot.reply_to(
            message,
            f"✅ Выговор снят!\n"
            f"⚠ Осталось: {scores[uid]['warnings']}"
        )

    # ===== ОТГУЛ =====
    elif "отгул" in text:

        if scores[uid]["points"] < 15:
            bot.reply_to(message, "❌ Нужно 15 баллов")
            return

        scores[uid]["points"] -= 15

        now = datetime.datetime.now()

        if not scores[uid]["vacation_end"]:
            end_time = now + datetime.timedelta(hours=24)
        else:
            try:
                current_end = datetime.datetime.strptime(
                    scores[uid]["vacation_end"],
                    "%Y-%m-%d %H:%M:%S.%f"
                )
                if current_end < now:
                    current_end = now
            except:
                current_end = now

            end_time = current_end + datetime.timedelta(hours=24)

        scores[uid]["vacation_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        bot.reply_to(
            message,
            f"🌴 Отгул продлён!\n"
            f"До: {end_time.strftime('%d.%m.%Y %H:%M')}"
        )

    save_db(scores)

# =========================
# ВЫГОВОРЫ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("#выговор"))
def warning(message):

    admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]

    if message.from_user.id not in admins:
        return

    match = re.search(r"#выговор\s+@?(\w+)", message.text.lower())
    if not match:
        bot.reply_to(message, "Укажи пользователя")
        return

    username = match.group(1)
    parts = message.text.split("\n")
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    target = find_user(username)

    if not target:
        bot.reply_to(message, "❌ Пользователь не найден")
        return

    scores[target]["warnings"] += 1
    num = scores[target]["warnings"]

    text = (
        f"━━━━━━━━━━━━━━━\n"
        f"⚠ Выговор {num}/3\n"
        f"👤 {scores[target]['name']}\n"
        f"👮 Выдал: {message.from_user.first_name}\n\n"
        f"📝 Причина:\n{reason}\n"
        f"━━━━━━━━━━━━━━━"
    )

    bot.send_message(GROUP_ID, text, message_thread_id=WARNING_THREAD)

    save_db(scores)

print("Bot started")
bot.infinity_polling()

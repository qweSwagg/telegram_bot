import telebot
import json
import re
import os
import random
import datetime

TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

OWNER_ID = 7548603865
GROUP_ID = -1003850339565

BALANCE_THREAD = 685
WARNING_THREAD = 865

# =====================
# БАЗА ДАННЫХ
# =====================

def load_scores():
    try:
        with open("scores.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_scores(data):
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

scores = load_scores()

# =====================
# ДАННЫЕ
# =====================

vacation_time = {}
purchase_history = []

phrases = [
    "Так держать!",
    "Молодец!",
    "Хорошо постарался!",
    "Отличная работа!",
    "Продолжай в том же духе!"
]

# =====================
# ПОИСК ПОЛЬЗОВАТЕЛЯ
# =====================

def find_user(username):
    username = username.lower()
    for uid, data in scores.items():
        if username in data["name"].lower():
            return uid
    return None

# =====================
# ДОБАВЛЕНИЕ БАЛЛОВ
# =====================

@bot.message_handler(func=lambda m: m.text and re.search(r"#баллы", m.text.lower()))
def add_points(message):

    if re.search(r"#балы", message.text.lower()):
        bot.reply_to(message, "Ты неправильно подал заявку! Посмотри как правильно и повтори!")
        return

    bot.forward_message(
        GROUP_ID,
        message.chat.id,
        message.message_id,
        message_thread_id=BALANCE_THREAD
    )

    uid = str(message.from_user.id)
    name = message.from_user.first_name

    match_owner = re.search(r"#баллы\s+@?(\w+)\s+(\d+)", message.text.lower())
    match_self = re.search(r"#баллы\s+(\d+)", message.text.lower())

    # Владелец может добавлять другим
    if match_owner and message.from_user.id == OWNER_ID:

        username = match_owner.group(1)
        points = int(match_owner.group(2))

        target = find_user(username)

        if not target:
            bot.reply_to(message, "Пользователь не найден")
            return

        scores[target]["points"] += points

    else:

        if not match_self:
            return

        points = int(match_self.group(1))

        if uid not in scores:
            scores[uid] = {"name": name, "points": 0, "warnings": 0}

        scores[uid]["points"] += points

        bot.reply_to(
            message,
            f"Баллы добавлены в твой личный банк! 
у тебя {scores[uid]['points']} баллов "
        )

    save_scores(scores)

    total = scores[uid]["points"]

    bot.send_message(
        GROUP_ID,
        f"{random.choice(phrases)}\n"
        f"{name}\nБаллы: {total}",
        message_thread_id=BALANCE_THREAD
    )

# =====================
# РЕЙТИНГ
# =====================

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

    for i, user in enumerate(sorted_users[:10], 1):

        medal = ""
        if i == 1:
            medal = "🥇 Самый лучший!"
        elif i == 2:
            medal = "🥈Ты почти лучший!"
        elif i == 3:
            medal = "🥉Догоняй!"

        if i == len(sorted_users):
            medal += " Работай лучше!"

        text += f"{i}. {medal} {user['name']} — {user['points']} баллов\n"

    bot.reply_to(message, text)

# =====================
# МАГАЗИН
# =====================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!магазин"))
def shop(message):

    bot.reply_to(message,
"""
🛒 Магазин:

!купить выговор — 30 баллов
!купить отгул — 15 баллов
""")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!купить"))
def buy(message):

    uid = str(message.from_user.id)

    if uid not in scores:
        bot.reply_to(message, "Нет баллов")
        return

    text = message.text.lower()

    # Выговор
    if "выговор" in text:

        if scores[uid]["points"] < 30:
            bot.reply_to(message, "Нужно 30 баллов")
            return

        scores[uid]["points"] -= 30
        purchase_history.append(f"{message.from_user.first_name} снял выговор")

        bot.reply_to(message, "✅ Выговор снят")

    # Отгул
    elif "отгул" in text:

        if scores[uid]["points"] < 15:
            bot.reply_to(message, "Нужно 15 баллов")
            return

        scores[uid]["points"] -= 15

        end = datetime.datetime.now() + datetime.timedelta(hours=24)
        vacation_time[uid] = end

        purchase_history.append(
            f"{message.from_user.first_name} купил отгул до {end}"
        )

        bot.reply_to(
            message,
            f"🎉 Отдых до: {end.strftime('%d.%m.%Y %H:%M')}"
        )

    save_scores(scores)

# =====================
# ИСТОРИЯ (АДМИНЫ)
# =====================

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "!история")
def history(message):

    admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]

    if message.from_user.id not in admins:
        return

    bot.reply_to(message, "\n".join(purchase_history[-20:]))

# =====================
# ВЫГОВОРЫ
# =====================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("#выговор"))
def warnings(message):

    admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]

    if message.from_user.id not in admins:
        return

    bot.forward_message(
        GROUP_ID,
        message.chat.id,
        message.message_id,
        message_thread_id=WARNING_THREAD
    )

    match = re.search(r"#выговор\s+@?(\w+)", message.text.lower())

    if not match:
        return

    username = match.group(1)

    parts = message.text.split("\n")
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    target = find_user(username)

    if not target:
        return

    scores[target]["warnings"] += 1
    num = scores[target]["warnings"]

    text = f"""
⚠️ Выговор!

Пользователь: {scores[target]['name']}
Выдал: {message.from_user.first_name}

Выговора: {num}/3
Причина: {reason}
"""

    if num == 1:
        text += "Будь осторожнее ⚠️"
    elif num == 2:
        text += "Повышение под угрозой 😬"
    elif num == 3:
        text += "❌ Всё плохо"

    bot.send_message(
        GROUP_ID,
        text,
        message_thread_id=WARNING_THREAD
    )

    save_scores(scores)

print("Bot started")
bot.infinity_polling()
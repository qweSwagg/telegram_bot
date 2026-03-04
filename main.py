import telebot
import json
import re
import os

TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

OWNER_ID = 7548603865

# =========================
# БАЗА ДАННЫХ
# =========================

def load_json():
    try:
        with open("scores.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(data):
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

scores = load_json()

DETAIL_TEXT = "Владелец пока не добавил описание"

# =========================
# ДОБАВЛЕНИЕ БАЛЛОВ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("#баллы"))
def add_points(message):

    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name

    match = re.search(r"#баллы\s*[+]?\s*(\d+)", message.text.lower())
    if not match:
        return

    points = int(match.group(1))

    if user_id not in scores:
        scores[user_id] = {"name": user_name, "points": 0}

    scores[user_id]["points"] += points

    save_json(scores)

    bot.reply_to(
        message,
        f"Ваши баллы добавлены в личный банк!\nТеперь: {scores[user_id]['points']} баллов"
    )

# =========================
# СНЯТИЕ БАЛЛОВ (АДМИНЫ)
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("-баллы"))
def remove_points(message):

    if message.from_user.id not in [
        admin.user.id for admin in bot.get_chat_administrators(message.chat.id)
    ]:
        bot.reply_to(message, "Только админы могут снимать баллы")
        return

    match = re.search(r"-баллы\s+@?(\w+)\s+(\d+)", message.text.lower())
    if not match:
        return

    username = match.group(1)
    points = int(match.group(2))

    for uid, data in scores.items():
        if username.lower() in data["name"].lower():
            scores[uid]["points"] = max(0, scores[uid]["points"] - points)

    save_json(scores)

    bot.reply_to(message, "Баллы сняты")

# =========================
# РЕЙТИНГ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!баллы"))
def show_scores(message):

    args = message.text.lower().split()

    # ===== Подробнее =====
    if len(args) >= 2 and args[1] == "подробнее":

        if message.from_user.id != OWNER_ID:
            return

        global DETAIL_TEXT
        DETAIL_TEXT = message.text.split(maxsplit=2)[2]

        bot.reply_to(message, "Описание обновлено")
        return

    # ===== Рейтинг =====
    if len(args) >= 2 and args[1] == "вся":

        if not scores:
            bot.reply_to(message, "Нет участников")
            return

        sorted_scores = sorted(
            scores.values(),
            key=lambda x: x["points"],
            reverse=True
        )

        text = "🏆 Рейтинг участников\n\n"

        for i, data in enumerate(sorted_scores, 1):

            if i == 1:
                place = "Самый лучший!"
            elif i == 2:
                place = "Почти лучший!"
            elif i == 3:
                place = "Третье место!"
            else:
                place = ""

            if data["points"] == 0:
                place = "Работай!"

            text += f"{i}. {data['name']} — {data['points']} {place}\n"

        bot.reply_to(message, text)
        return

    # ===== Свои баллы =====
    uid = str(message.from_user.id)

    if uid in scores:
        bot.reply_to(message, f"У тебя {scores[uid]['points']} баллов")
    else:
        bot.reply_to(message, "У тебя 0 баллов. Работай!")

# =========================
# ПОДРОБНЕЕ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "!подробнее")
def show_detail(message):
    bot.reply_to(message, f"📜 Подробнее\n\n{DETAIL_TEXT}")

print("Bot started")
bot.polling(none_stop=True)

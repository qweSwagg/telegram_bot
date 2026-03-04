import telebot
import json
import re
from datetime import datetime

TOKEN = 8711311798:AAEXH87AxZQcoqA6YRlRHSa8LynUq_JIIrE

GROUP_ID = -1003850339565
THREAD_ID = 685
OWNER_ID = 7548603865

bot = telebot.TeleBot(TOKEN)

# =========================
# БАЗА ДАННЫХ
# =========================

def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

scores = load_json("scores.json", {})
history = load_json("history.json", {})

DETAIL_TEXT = "Владелец пока не добавил описание"

# =========================
# ПОИСК ПОЛЬЗОВАТЕЛЯ (УЛУЧШЕННЫЙ)
# =========================

def find_user(username):
    username = username.lower()

    for uid, data in scores.items():
        if username == str(uid):
            return uid

        if username in data["name"].lower():
            return uid

        if "username" in data and username in data["username"].lower():
            return uid

    return None

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
    save_json("scores.json", scores)

    # Ответ в чат
    bot.reply_to(
        message,
        f"Ваши баллы добавлены в личный банк.\nСпасибо за модерацию чата!\nТеперь: {scores[user_id]['points']} баллов"
    )

# =========================
# СНЯТИЕ БАЛЛОВ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("-баллы"))
def remove_points(message):

    admins = [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]

    if message.from_user.id not in admins:
        bot.reply_to(message, "Только админы могут снимать баллы")
        return

    match = re.search(r"-баллы\s+@?(\w+)\s+(\d+)", message.text.lower())
    if not match:
        return

    username = match.group(1)
    points = int(match.group(2))

    target = find_user(username)

    if not target:
        bot.reply_to(message, "Пользователь не найден")
        return

    scores[target]["points"] = max(0, scores[target]["points"] - points)

    save_json("scores.json", scores)

    bot.reply_to(message, "Баллы сняты")

# =========================
# РЕЙТИНГ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!баллы"))
def show_scores(message):

    args = message.text.lower().split()

    # ===== Подробно =====
    if len(args) >= 2 and args[1] == "подробнее":
        if message.from_user.id != OWNER_ID:
            return

        global DETAIL_TEXT
        DETAIL_TEXT = message.text.split(maxsplit=2)[2]

        bot.reply_to(message, "Описание обновлено")
        return

    # ===== Рейтинг =====
    if len(args) >= 2 and args[1] == "вся":

        # Показываем всех пользователей
        sorted_scores = sorted(scores.values(),
                               key=lambda x: x["points"],
                               reverse=True)

        text = "🏆 Рейтинг участников\n\n"

        for i, data in enumerate(sorted_scores, 1):

            # Модели топ 3
            if i == 1:
                place_text = "Самый лучший!"
            elif i == 2:
                place_text = "Почти лучший!"
            elif i == 3:
                place_text = "Третье место!"
            else:
                place_text = ""

            if data["points"] == 0:
                place_text = "Работай!"

            text += f"{i}. {data['name']} — {data['points']} {place_text}\n"

        bot.reply_to(message, text)
        return

    # Свои баллы
    uid = str(message.from_user.id)

    if uid in scores:
        bot.reply_to(message,
                     f"У тебя {scores[uid]['points']} баллов")
    else:
        bot.reply_to(message, "У тебя 0 баллов. Работай!")

# =========================
# ПОДРОБНЕЕ
# =========================

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "!подробнее")
def show_detail(message):

    bot.reply_to(
        message,
        f"📜 Подробнее\n\n{DETAIL_TEXT}"
    )

print("Bot started")
bot.infinity_polling()

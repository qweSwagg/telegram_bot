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

# =========================
# БАЗА ДАННЫХ
# =========================

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

# =========================
# ФРАЗЫ
# =========================

good_phrases = [
    "Отличная работа!",
    "Молодец!",
    "Так держать!",
    "Хорошо постарался!"
]

# =========================
# ПОИСК
# =========================

def find_user(username):
    username = username.lower()
    for uid, data in scores.items():
        if username in data["name"].lower():
            return uid
    return None

# =========================
# ДОБАВЛЕНИЕ БАЛЛОВ
# =========================

@bot.message_handler(func=lambda m: m.text and re.search(r"#баллы", m.text.lower()))
def add_points(message):

    # Пересылка сообщения (без похвалы)
    bot.forward_message(
        GROUP_ID,
        message.chat.id,
        message.message_id,
        message_thread_id=BALANCE_THREAD
    )

    text = message.text.lower()

    # Проверка ошибки
    if re.search(r"#балы", text):
        bot.reply_to(message, "Ты неправильно подал заявку! Посмотри как правильно и повтори!")
        return

    uid = str(message.from_user.id)
    name = message.from_user.first_name

    match = re.search(r"#баллы\s*[+]?\s*(\d+)", text)

    if not match:
        return

    points = int(match.group(1))

    if uid not in scores:
        scores[uid] = {
            "name": name,
            "points": 0,
            "warnings": 0
        }

    scores[uid]["points"] += points

    save_scores(scores)

    # Ответ пользователю (без похвалы)
    bot.reply_to(
        message,
        f"Баллы {points} добавлены!\nТвой банк: {scores[uid]['points']} баллов"
    )

    # Сообщение в ветку
    bot.send_message(
        GROUP_ID,
        f"{name}\nБаллы: {scores[uid]['points']}",
        message_thread_id=BALANCE_THREAD
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

    for i, user in enumerate(sorted_users[:10], 1):

        medal = ""

        if i == 1:
            medal = "🥇 Самый лучший!"
        elif i == 2:
            medal = "🥈 Ты почти лучший!"
        elif i == 3:
            medal = "🥉 Работай усерднее!"

        text += f"{i}. {user['name']} — {user['points']} баллов {medal}\n"

    bot.reply_to(message, text)

# =========================
# МАГАЗИН
# =========================

@bot.message_handler(func=lambda m: m.text and "!магазин" in m.text.lower())
def shop(message):

    bot.reply_to(
        message,
"""
🛒 Магазин

Привет! Это магазин.
Тут ты можешь снять выговор или купить отгул на сутки.

Стоимость:
- Снять выговор → 30 баллов
- Отгул → 15 баллов

Чтобы купить:
!купить выговор
!купить отгул
"""
    )

# =========================
# ПОКУПКИ
# =========================

@bot.message_handler(func=lambda m: m.text and "!купить" in m.text.lower())
def buy(message):

    uid = str(message.from_user.id)

    if uid not in scores:
        bot.reply_to(message, "У тебя нет баллов")
        return

    text = message.text.lower()

    # ===== Выговор =====
    if "выговор" in text:

        if scores[uid]["points"] < 30:
            bot.reply_to(message, "Нужно 30 баллов")
            return

        scores[uid]["points"] -= 30
        scores[uid]["warnings"] = max(0, scores[uid]["warnings"] - 1)

        bot.reply_to(
            message,
            f"✅ Выговор снят!\nВыговоров осталось: {scores[uid]['warnings']}"
        )

    # ===== Отгул =====
    elif "отгул" in text:

        if scores[uid]["points"] < 15:
            bot.reply_to(message, "Нужно 15 баллов")
            return

        scores[uid]["points"] -= 15

        end = datetime.datetime.now() + datetime.timedelta(hours=24)

        bot.reply_to(
            message,
            f"""
🎉 Ты купил отгул!

Отдых до:
{end.strftime('%d.%m.%Y %H:%M')}
"""
        )

    save_scores(scores)

print("Bot started")
bot.infinity_polling()
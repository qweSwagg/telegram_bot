import telebot
import json
import os
import re
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

GROUP_ID = -1003850339565

BALANCE_THREAD = 685
WARNING_THREAD = 865
SHOP_THREAD = 952

DATA_FILE = "scores.json"
LOG_FILE = "logs.txt"

# -------------------- БАЗА --------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {text}\n")

data = load_data()

def get_user(user):
    user_id = str(user.id)
    if user_id not in data:
        data[user_id] = {
            "name": user.first_name,
            "points": 0,
            "warnings": 0,
            "vacation_end": None
        }
    return data[user_id]

def check_vacation(user_id):
    user = data[user_id]
    if user["vacation_end"]:
        try:
            end = datetime.strptime(user["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
            if datetime.now() > end:
                user["vacation_end"] = None
        except:
            user["vacation_end"] = None

# -------------------- БАЛЛЫ --------------------

@bot.message_handler(regexp=r"#баллы\s+[+-]?\d+")
def add_points(message):
    if message.chat.id != GROUP_ID:
        return

    amount = int(re.findall(r"[+-]?\d+", message.text)[0])

    if not message.reply_to_message:
        bot.reply_to(message, "Ответьте на сообщение пользователя.")
        return

    user = get_user(message.reply_to_message.from_user)
    user["points"] += amount

    save_data(data)
    log(f"{user['name']} получил {amount} баллов")

    bot.send_message(GROUP_ID,
                     f"💰 {user['name']} получил {amount} баллов\n"
                     f"Баланс: {user['points']}",
                     message_thread_id=BALANCE_THREAD)

# -------------------- МОИ БАЛЛЫ --------------------

@bot.message_handler(regexp=r"!мои баллы")
def my_points(message):
    user = get_user(message.from_user)
    check_vacation(str(message.from_user.id))
    bot.reply_to(message, f"💰 Ваш баланс: {user['points']}")

# -------------------- РЕЙТИНГ --------------------

@bot.message_handler(regexp=r"!баллы")
def rating(message):
    sorted_users = sorted(data.values(), key=lambda x: x["points"], reverse=True)
    text = "🏆 Рейтинг:\n\n"
    for i, u in enumerate(sorted_users[:10], 1):
        text += f"{i}. {u['name']} — {u['points']} баллов\n"
    bot.send_message(message.chat.id, text)

# -------------------- ВЫГОВОР --------------------

@bot.message_handler(regexp=r"#выговор")
def warning(message):
    if message.chat.id != GROUP_ID:
        return

    if not message.reply_to_message:
        bot.reply_to(message, "Ответьте на сообщение пользователя.")
        return

    user = get_user(message.reply_to_message.from_user)
    user["warnings"] += 1

    save_data(data)
    log(f"{user['name']} получил выговор")

    bot.send_message(GROUP_ID,
                     f"⚠ {user['name']} получил выговор ({user['warnings']})",
                     message_thread_id=WARNING_THREAD)

# -------------------- МАГАЗИН --------------------

@bot.message_handler(regexp=r"!магазин")
def shop(message):
    if message.message_thread_id != SHOP_THREAD:
        return

    text = (
        "🛒 Магазин:\n\n"
        "🎯 Снять выговор — 30 баллов\n"
        "🌴 Отгул (24 часа) — 15 баллов"
    )
    bot.send_message(message.chat.id, text)

# -------------------- КУПИТЬ ОТГУЛ --------------------

@bot.message_handler(regexp=r"!купить отгул")
def buy_vacation(message):
    user_id = str(message.from_user.id)
    user = get_user(message.from_user)
    check_vacation(user_id)

    if user["points"] < 15:
        bot.reply_to(message, "❌ Недостаточно баллов.")
        return

    user["points"] -= 15

    now = datetime.now()
    if user["vacation_end"]:
        end = datetime.strptime(user["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
        end += timedelta(hours=24)
    else:
        end = now + timedelta(hours=24)

    user["vacation_end"] = end.strftime("%Y-%m-%d %H:%M:%S.%f")

    save_data(data)
    log(f"{user['name']} купил отгул")

    bot.reply_to(message, f"🌴 Отгул до {end}")

# -------------------- СНЯТЬ ВЫГОВОР --------------------

@bot.message_handler(regexp=r"!купить выговор")
def remove_warning(message):
    user = get_user(message.from_user)

    if user["points"] < 30:
        bot.reply_to(message, "❌ Недостаточно баллов.")
        return

    if user["warnings"] <= 0:
        bot.reply_to(message, "⚠ У вас нет выговоров.")
        return

    user["points"] -= 30
    user["warnings"] -= 1

    save_data(data)
    log(f"{user['name']} снял выговор")

    bot.reply_to(message, f"✅ Выговор снят. Осталось: {user['warnings']}")

print("Бот запущен...")
bot.infinity_polling()

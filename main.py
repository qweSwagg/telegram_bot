import telebot
import json
import os
import datetime

TOKEN = os.getenv("TOKEN")  # Вставь сюда токен бота или через Environment Variables
bot = telebot.TeleBot(TOKEN)

OWNER_ID = 7548603865

GROUP_ID = -1003850339565
BALANCE_THREAD = 685
WARNING_THREAD = 865
SHOP_THREAD = 952

# Файлы базы рядом с main.py
USERS_FILE = "users.json"
WARNS_FILE = "warns.json"

# Создаем файлы если их нет
for file in [USERS_FILE, WARNS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)


def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_warns():
    with open(WARNS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_warns(data):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Регистрируем всех пользователей, чтобы бот их видел
def register_user(user):
    users = load_users()
    uid = str(user.id)
    if uid not in users:
        users[uid] = {"username": user.username, "points": 0}
    else:
        users[uid]["username"] = user.username  # обновляем username
    save_users(users)


# =========================
# КОМАНДЫ И СОБЫТИЯ
# =========================

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    register_user(message.from_user)
    text = message.text.lower() if message.text else ""

    # Команда: !мой банк
    if text == "!мой банк":
        users = load_users()
        uid = str(message.from_user.id)
        points = users.get(uid, {}).get("points", 0)
        bot.reply_to(message, f"💰 В вашем личном банке {points} баллов")

    # Команда: #выговор
    if text.startswith("#выговор"):
        if not message.reply_to_message:
            bot.reply_to(message, "❌ Ответьте на сообщение пользователя, которому хотите выдать выговор")
            return

        admin = message.from_user
        target = message.reply_to_message.from_user

        warns = load_warns()
        target_id = str(target.id)
        warns[target_id] = warns.get(target_id, 0) + 1
        save_warns(warns)

        admin_user = f"@{admin.username}" if admin.username else admin.first_name
        target_user = f"@{target.username}" if target.username else target.first_name

        bot.send_message(
            message.chat.id,
            f"{admin_user} выговор успешно выдан админу {target_user}\n\n"
            f"{target_user} будь осторожнее!"
        )

    # Команда: #баллы +число
    if "#баллы" in text:
        import re
        match = re.search(r"#баллы\s*[+]?\s*(\d+)", text)
        if not match:
            return
        points = int(match.group(1))

        uid = str(message.from_user.id)
        users = load_users()
        if uid not in users:
            users[uid] = {"username": message.from_user.username, "points": 0}

        users[uid]["points"] += points
        save_users(users)

        bot.send_message(GROUP_ID, "🎁", message_thread_id=BALANCE_THREAD)
        bot.forward_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=BALANCE_THREAD)
        bot.send_message(
            GROUP_ID,
            f"━━━━━━━━━━━━━━━\n"
            f"👤 {message.from_user.first_name}\n"
            f"🏦 Твой банк: {users[uid]['points']} баллов\n"
            f"━━━━━━━━━━━━━━━",
            message_thread_id=BALANCE_THREAD
        )
        bot.reply_to(message, f"💰 Баллы {points} добавлены!\n🏦 Сейчас у тебя {users[uid]['points']} баллов")

    # Команда: !баллы (рейтинг)
    if text.startswith("!баллы"):
        users = load_users()
        if not users:
            bot.reply_to(message, "Нет участников")
            return

        sorted_users = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
        text_out = "🏆 Рейтинг участников\n\n"
        for i, (uid, user) in enumerate(sorted_users, 1):
            medal = ""
            if i == 1:
                medal = " Самый лучший!"
            elif i == 2:
                medal = " Ты почти лучший!"
            elif i == 3:
                medal = " Работай усерднее!"
            icon = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else "▫"
            text_out += f"{icon} {user['username'] or user['username']} — {user['points']} баллов{medal}\n"
        bot.reply_to(message, text_out)

print("Бот запущен!")
bot.infinity_polling()
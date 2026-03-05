import telebot
import json
import os
import re
import datetime
import threading
import time

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

OWNER_ID = 7548603865

GROUP_ID = -1003850339565
BALANCE_THREAD = 685
WARNING_THREAD = 865
SHOP_THREAD = 952

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


# =========================
# Регистрация пользователя
# =========================
def register_user(user):
    users = load_users()
    uid = str(user.id)
    if uid not in users:
        users[uid] = {"username": user.username, "points": 0, "vacation_end": None}
    else:
        users[uid]["username"] = user.username
    save_users(users)


# =========================
# Поиск пользователя по username или id
# =========================
def find_user(identifier):
    identifier = identifier.lower().replace("@", "")
    users = load_users()
    for uid, data in users.items():
        if identifier == str(uid):
            return uid
        if "username" in data and data["username"] and identifier == data["username"].lower():
            return uid
    return None


# =========================
# Словарь для последнего сообщения выговора
last_warn_message = {}


# =========================
# Проверка и уведомление об окончании отгула
def vacation_checker():
    while True:
        users = load_users()
        for uid, data in users.items():
            if "vacation_end" in data and data["vacation_end"]:
                end_time = datetime.datetime.strptime(data["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
                if datetime.datetime.now() >= end_time:
                    user_name = f"@{data['username']}" if data.get("username") else "Пользователь"
                    bot.send_message(GROUP_ID, f"⏰ {user_name} твой отгул окончился, приступай к работе!")
                    users[uid]["vacation_end"] = None
                    save_users(users)
        time.sleep(60)


# =========================
# Склонение слов "балл"
def points_text(amount):
    if amount == 1:
        return "1 балл"
    elif 2 <= amount <= 4:
        return f"{amount} балла"
    else:
        return f"{amount} баллов"


# =========================
# Обработчик сообщений
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    register_user(message.from_user)
    users = load_users()
    warns = load_warns()
    text = message.text.lower() if message.text else ""
    uid = str(message.from_user.id)

    # ===== !мой банк =====
    if text == "!мой банк":
        points = users.get(uid, {}).get("points", 0)
        bot.reply_to(message, f"💰 В вашем личном банке {points} {points_text(points)}")

    # ===== #баллы +число =====
    if "#баллы" in text:
        match = re.search(r"#баллы\s*[+]?\s*(\d+)", text)
        if not match:
            return
        points = int(match.group(1))
        if uid not in users:
            users[uid] = {"username": message.from_user.username, "points": 0, "vacation_end": None}
        users[uid]["points"] += points
        save_users(users)
        # Сообщение в тему баллов
        bot.send_message(GROUP_ID, "🎁", message_thread_id=BALANCE_THREAD)
        bot.forward_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=BALANCE_THREAD)
        bot.send_message(
            GROUP_ID,
            f"━━━━━━━━━━━━━━━\n👤 {message.from_user.first_name}\n🏦 Твой банк: {users[uid]['points']} {points_text(users[uid]['points'])}\n━━━━━━━━━━━━━━━",
            message_thread_id=BALANCE_THREAD
        )
        bot.reply_to(message, f"💰 Баллы {points_text(points)} добавлены!\n🏦 Сейчас у тебя {points_text(users[uid]['points'])}")

    # ===== !баллы =====
    if text.startswith("!баллы"):
        if not users:
            bot.reply_to(message, "Нет участников")
            return
        sorted_users = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
        text_out = "🏆 Рейтинг участников\n\n"
        for i, (uid2, user) in enumerate(sorted_users, 1):
            medal = ""
            if i == 1:
                medal = " Самый лучший!"
            elif i == 2:
                medal = " Ты почти лучший!"
            elif i == 3:
                medal = " Работай усерднее!"
            icon = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else "▫"
            text_out += f"{icon} {user['username']} — {user['points']} {points_text(user['points'])}{medal}\n"
        bot.reply_to(message, text_out)

    # ===== !магазин =====
    if text == "!магазин":
        if message.message_thread_id != SHOP_THREAD:
            return
        bot.reply_to(
            message,
            "🛒 Магазин\n\n🎯 Снять выговор — 30 баллов\n🌴 Отгул — 15 баллов (суммируется)\n\nКоманды:\n!купить выговор\n!купить отгул"
        )

    # ===== !купить =====
    if text.startswith("!купить"):
        if message.message_thread_id != SHOP_THREAD:
            return
        if uid not in users:
            bot.reply_to(message, "❌ У тебя нет баллов")
            return
        # Выговор
        if "выговор" in text:
            if users[uid]["points"] < 30:
                bot.reply_to(message, "❌ Нужно 30 баллов")
                return
            users[uid]["points"] -= 30
            warns[uid] = max(0, warns.get(uid, 0) - 1)
            save_warns(warns)
            save_users(users)
            # удаляем последнее сообщение с выговором
            if uid in last_warn_message:
                try:
                    bot.delete_message(GROUP_ID, last_warn_message[uid])
                except:
                    pass
                last_warn_message.pop(uid)
            bot.reply_to(message, f"✅ Выговор снят! ⚠ Осталось: {warns.get(uid,0)}")
        # Отгул
        elif "отгул" in text:
            if users[uid]["points"] < 15:
                bot.reply_to(message, "❌ Нужно 15 баллов")
                return
            users[uid]["points"] -= 15
            now = datetime.datetime.now()
            if users[uid].get("vacation_end"):
                users[uid]["vacation_end"] = datetime.datetime.strptime(users[uid]["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
            else:
                users[uid]["vacation_end"] = now
            users[uid]["vacation_end"] += datetime.timedelta(hours=24)
            save_users(users)
            bot.reply_to(message, f"🌴 Отгул продлён! До: {users[uid]['vacation_end'].strftime('%d.%m.%Y %H:%M')}")

    # ===== #выговор @username =====
    if text.startswith("#выговор"):
        parts = message.text.split("\n")
        first_line = parts[0]
        reason = parts[1] if len(parts) > 1 else "Причина не указана"
        match = re.search(r"#выговор\s+@?(\w+)", first_line)
        if not match:
            bot.reply_to(message, "❌ Используйте: #выговор @username")
            return
        target_username = match.group(1)
        target_id = find_user(target_username)
        if not target_id:
            bot.reply_to(message, f"❌ Пользователь @{target_username} не найден")
            return
        warns[target_id] = warns.get(target_id, 0) + 1
        save_warns(warns)

        admin_user = f"🎩 @{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        target_user = f"⚠ @{users[target_id]['username']}" if users[target_id].get("username") else target_username

        # Отправка в тему выговоров
        msg = bot.send_message(
            GROUP_ID,
            f"⚠ Выговор {warns[target_id]}/3\n👤 {target_user}\n👮 Выдал: {admin_user}\n\n📝 Причина:\n{reason}",
            message_thread_id=WARNING_THREAD
        )
        last_warn_message[target_id] = msg.message_id

        # Сообщение в чат с эмодзи красиво
        bot.send_message(
            GROUP_ID,
            f"🎯 {admin_user} выговор успешно выдан админу {target_user}\n\n⏰ {target_user} будь осторожнее!"
        )

    # ===== !подарить баллы (только OWNER) =====
    if text.startswith("!подарить баллы"):
        if message.from_user.id != OWNER_ID:
            return
        match = re.search(r"!подарить баллы\s+@?(\w+)\s+(\d+)", message.text)
        target_id = None
        amount = 0
        if message.reply_to_message:
            target_id = str(message.reply_to_message.from_user.id)
            amount = int(message.text.split()[-1])
        elif match:
            target_username = match.group(1)
            target_id = find_user(target_username)
            amount = int(match.group(2))
        if not target_id or amount <= 0:
            return
        if target_id not in users:
            users[target_id] = {"username": None, "points": 0, "vacation_end": None}
        users[target_id]["points"] += amount
        save_users(users)
        sender = f"@{message.from_user.username}" if message.from_user.username else "Владелец"
        receiver = f"@{users[target_id]['username']}" if users[target_id].get("username") else "Пользователь"
        bot.send_message(
            GROUP_ID,
            f"🎁 Поздравляю {receiver}, тебе подарили {points_text(amount)}!\n\n👏 Благодари {sender} за щедрость!"
        )

    # ===== !дать баллы (для всех) =====
    if text.startswith("!дать баллы"):
        target_id = None
        amount = 0
        if message.reply_to_message:
            target_id = str(message.reply_to_message.from_user.id)
            try:
                amount = int(message.text.split()[-1])
            except:
                return
        else:
            match = re.search(r"!дать баллы\s+@?(\w+)\s+(\d+)", message.text)
            if match:
                target_username = match.group(1)
                target_id = find_user(target_username)
                amount = int(match.group(2))
        if not target_id or amount <= 0:
            return
        if uid not in users or users[uid]["points"] < amount:
            bot.reply_to(message, "❌ У вас недостаточно баллов")
            return
        if target_id not in users:
            users[target_id] = {"username": None, "points": 0, "vacation_end": None}
        users[uid]["points"] -= amount
        users[target_id]["points"] += amount
        save_users(users)
        giver = f"@{users[uid]['username']}" if users[uid].get("username") else "Пользователь"
        receiver = f"@{users[target_id]['username']}" if users[target_id].get("username") else "Пользователь"
        bot.send_message(
            GROUP_ID,
            f"🎁 Поздравляю {receiver}, ты получил {points_text(amount)}!\n\n👏 Благодари {giver} за щедрость!"
        )


# =========================
# Запуск проверки отгулов
threading.Thread(target=vacation_checker, daemon=True).start()

print("Бот запущен!")
bot.infinity_polling()
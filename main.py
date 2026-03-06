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

# =========================
# Создание файлов, если их нет
# =========================
for file in [USERS_FILE, WARNS_FILE]:
    if not os.path.exists(file) or os.path.getsize(file) == 0:
        with open(file, "w", encoding="utf-8") as f:
            f.write("{}")

# =========================
# Работа с базой
# =========================
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
# Склонение баллов
# =========================
def points_text(amount):
    if amount == 1:
        return "1 балл"
    elif 2 <= amount <= 4:
        return f"{amount} балла"
    else:
        return f"{amount} баллов"


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
# Поиск пользователя
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
# Последние сообщения выговоров для удаления
# =========================
last_warn_messages = {}  # {user_id: [msg_id1, msg_id2, msg_id3]}


# =========================
# Проверка окончания отгула
# =========================
def vacation_checker():
    while True:
        users = load_users()
        changed = False
        for uid, data in users.items():
            if data.get("vacation_end"):
                try:
                    end_time = datetime.datetime.strptime(data["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
                    if datetime.datetime.now() >= end_time:
                        user_name = f"@{data['username']}" if data.get("username") else "Пользователь"
                        bot.send_message(GROUP_ID, f"⏰ {user_name} твой отгул окончился, приступай к работе!")
                        users[uid]["vacation_end"] = None
                        changed = True
                except Exception as e:
                    print("Ошибка парсинга vacation_end:", e)
        if changed:
            save_users(users)
        time.sleep(60)


# =========================
# Все команды
# =========================
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    if not message.text:
        return
    register_user(message.from_user)
    users = load_users()
    warns = load_warns()
    text = message.text.lower()
    uid = str(message.from_user.id)

    # ===== !мой банк =====
    if text == "!мой банк":
        points = users.get(uid, {}).get("points", 0)
        bot.reply_to(message, f"💰 В вашем личном банке {points_text(points)}")

    # ===== #баллы =====
    if "#баллы" in text:
        match = re.search(r"#баллы\s*[+]?\s*(\d+)", text)
        if not match:
            return
        points = int(match.group(1))
        users[uid]["points"] += points
        save_users(users)

        bot.send_message(GROUP_ID, "🎁", message_thread_id=BALANCE_THREAD)
        bot.forward_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=BALANCE_THREAD)
        bot.send_message(
            GROUP_ID,
            f"━━━━━━━━━━━━━━━\n"
            f"👤 {message.from_user.first_name}\n"
            f"🏦 Твой банк: {points_text(users[uid]['points'])}\n"
            f"━━━━━━━━━━━━━━━",
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
            text_out += f"{icon} {user['username']} — {points_text(user['points'])}{medal}\n"
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
        # ===== Выговор =====
        if "выговор" in text:
            if warns.get(uid, 0) == 0:
                user_name = f"@{users[uid]['username']}" if users[uid].get("username") else "Пользователь"
                bot.reply_to(message, f"❌ {user_name} у тебя нет выговоров")
                return
            if users[uid]["points"] < 30:
                bot.reply_to(message, "❌ Нужно 30 баллов")
                return
            users[uid]["points"] -= 30
            warns[uid] = max(0, warns.get(uid, 0) - 1)
            save_warns(warns)
            save_users(users)
            # удаляем все сообщения выговора
            for msg_id in last_warn_messages.get(uid, []):
                try:
                    bot.delete_message(GROUP_ID, msg_id)
                except:
                    pass
            last_warn_messages.pop(uid, None)
            bot.reply_to(message, f"✅ Выговор снят! ⚠ Осталось: {warns.get(uid,0)}")
        # ===== Отгул =====
        elif "отгул" in text:
            if users[uid]["points"] < 15:
                bot.reply_to(message, "❌ Нужно 15 баллов")
                return
            users[uid]["points"] -= 15
            now = datetime.datetime.now()
            if users[uid].get("vacation_end"):
                try:
                    users[uid]["vacation_end"] = datetime.datetime.strptime(users[uid]["vacation_end"], "%Y-%m-%d %H:%M:%S.%f")
                except:
                    users[uid]["vacation_end"] = now
            else:
                users[uid]["vacation_end"] = now
            users[uid]["vacation_end"] += datetime.timedelta(hours=24)
            users[uid]["vacation_end"] = users[uid]["vacation_end"].strftime("%Y-%m-%d %H:%M:%S.%f")
            save_users(users)
            bot.reply_to(message, f"🌴 Отгул продлён! До: {users[uid]['vacation_end'][:16].replace('-', '.')}")

    # ===== #выговор =====
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

        bot.send_message(GROUP_ID, "⚠ Новый выговор", message_thread_id=WARNING_THREAD)
        bot.forward_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=WARNING_THREAD)
        msg = bot.send_message(
            GROUP_ID,
            f"━━━━━━━━━━━━━━━\n"
            f"⚠ Выговор {warns[target_id]}/3\n"
            f"👤 {target_user}\n"
            f"👮 Выдал: {admin_user}\n\n"
            f"📝 Причина:\n{reason}\n"
            f"━━━━━━━━━━━━━━━",
            message_thread_id=WARNING_THREAD
        )
        last_warn_messages[target_id] = [msg.message_id]
        bot.send_message(
            GROUP_ID,
            f"🎯 {admin_user} выговор успешно выдан админу {target_user}\n\n⏰ {target_user} будь осторожнее!"
        )

    # ===== !снять выговор ===== (только владелец) =====
    if text.startswith("!снять выговор"):
        if uid != str(OWNER_ID):
            bot.reply_to(message, "❌ Только владелец может использовать эту команду")
            return
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Укажи юзера: !снять выговор @username")
            return
        target_username = args[1].replace("@", "")
        target_id = find_user(target_username)
        if not target_id:
            bot.reply_to(message, f"❌ Пользователь @{target_username} не найден")
            return
        warns[target_id] = max(0, warns.get(target_id, 0) - 1)
        save_warns(warns)
        # удаляем все сообщения выговора
        for msg_id in last_warn_messages.get(target_id, []):
            try:
                bot.delete_message(GROUP_ID, msg_id)
            except:
                pass
        last_warn_messages.pop(target_id, None)
        target_name = f"@{users[target_id]['username']}" if users[target_id].get("username") else "Пользователь"
        bot.reply_to(message, f"🎉 {target_name} — возрадуйся! Тебе сняли выговор, поздравляю!")


# =========================
# Запуск проверки отгулов
# =========================
threading.Thread(target=vacation_checker, daemon=True).start()

print("Бот запущен!")
bot.infinity_polling()
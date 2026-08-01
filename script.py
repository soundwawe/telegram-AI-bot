import os
import json
import logging
import yt_dlp
from datetime import datetime, timedelta
import telebot
from telebot import types
from groq import Groq

# ---------------------------------------------------------
# CONFIGURATION & CONSTANTS
# ---------------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY_HERE")
BACKUP_CHANNEL_ID = os.getenv("BACKUP_CHANNEL_ID", None)

# VIP-пользователи и Админы (Telegram ID)
ADMIN_IDS = [123456789]

# 🎭 ХАРАКТЕР ИИ (System Prompt)
# Задай стиль общения твоего бота здесь:
AI_SYSTEM_PROMPT = "Ты вежливый, дружелюбный и современный виртуальный помощник супер-аппа. Отвечай кратко, по делу и с легким юмором."

# Пути к файлам базы данных
PROFILES_FILE = "profiles.json"
KEYS_FILE = "keys.json"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

INITIAL_KEYS = {
    "VIP_LIFETIME_888": {"type": "vip", "used": False},
    "VIP_FREE_PASS": {"type": "vip", "used": False}
}

user_profiles = {}
active_keys = INITIAL_KEYS


# ---------------------------------------------------------
# DATABASE & DATA PERSISTENCE
# ---------------------------------------------------------
def load_data():
    global user_profiles, active_keys
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                user_profiles = json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки profiles: {e}")
            user_profiles = {}

    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                active_keys = json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки keys: {e}")


def save_data():
    try:
        with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_profiles, f, ensure_ascii=False, indent=4)
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(active_keys, f, ensure_ascii=False, indent=4)

        if BACKUP_CHANNEL_ID:
            with open(PROFILES_FILE, 'rb') as f:
                bot.send_document(
                    BACKUP_CHANNEL_ID,
                    f,
                    caption=f"💾 Бэкап БД - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
    except Exception as e:
        logging.error(f"Ошибка сохранения: {e}")


def get_or_create_profile(user):
    user_id = str(user.id)
    if user_id not in user_profiles:
        trial_until = (datetime.now() + timedelta(days=7)).isoformat()
        user_profiles[user_id] = {
            "name": None,  # Спросим при первом запуске
            "username": user.username,
            "status": "free",  # "free" или "vip"
            "trial_until": trial_until,
            "playlist": [],  # Хранит дикты: {"title": ..., "file_id": ...}
            "notes": []
        }
        save_data()
    return user_profiles[user_id]


def check_access(user_id):
    if user_id in ADMIN_IDS or str(user_id) in [str(a) for a in ADMIN_IDS]:
        return True

    profile = user_profiles.get(str(user_id))
    if not profile:
        return False

    if profile.get("status") in ["vip", "pro"]:
        return True

    trial_until = profile.get("trial_until")
    if trial_until:
        try:
            until_dt = datetime.fromisoformat(trial_until)
            if datetime.now() < until_dt:
                return True
        except Exception:
            pass

    return False


# ---------------------------------------------------------
# KEYBOARDS
# ---------------------------------------------------------
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("🤖 Чат с ИИ"))
    keyboard.add(types.KeyboardButton("🎵 Поиск музыки"), types.KeyboardButton("🎧 Мой плейлист"))
    keyboard.add(types.KeyboardButton("📝 Заметки"), types.KeyboardButton("📅 Календарь"))
    keyboard.add(types.KeyboardButton("⚙️ Настройки"))
    return keyboard


# ---------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    profile = get_or_create_profile(message.from_user)

    # Если имя ещё не задано — спрашиваем
    if not profile.get("name"):
        msg = bot.send_message(message.chat.id, "Привет! 👋 Как мне к вам обращаться (как вас называть)?")
        bot.register_next_step_handler(msg, process_set_name_initial)
        return

    show_main_menu(message.chat.id, profile, message.from_user.id)


def process_set_name_initial(message):
    new_name = message.text.strip()
    profile = get_or_create_profile(message.from_user)
    profile["name"] = new_name
    save_data()
    bot.send_message(message.chat.id, f"Приятно познакомиться, *{new_name}*! ✨", parse_mode="Markdown")
    show_main_menu(message.chat.id, profile, message.from_user.id)


def show_main_menu(chat_id, profile, user_id):
    has_access = check_access(user_id)
    status_str = "VIP ✨" if profile.get("status") == "vip" else ("TRIAL ⏳" if has_access else "EXPIRED ❌")

    text = (
        f"📌 *Главное меню*\n"
        f"Обращение: *{profile.get('name')}*\n"
        f"Статус: *{status_str}*\n\n"
        f"Используйте кнопки снизу для навигации!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@bot.message_handler(commands=['key'])
def redeem_key(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Использование: `/key ВАШ_КЛЮЧ`", parse_mode="Markdown")
        return

    code = args[1].strip()
    if code in active_keys and not active_keys[code]["used"]:
        active_keys[code]["used"] = True
        profile = get_or_create_profile(message.from_user)
        profile["status"] = "vip"
        save_data()
        bot.reply_to(message, "🎉 *Ключ активирован!* Вам присвоен вечный **VIP** статус.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Неверный или уже использованный ключ.")


# ---------------------------------------------------------
# СОХРАНЕНИЕ АУДИО В ПЛЕЙЛИСТ ПРИ ОТПРАВКЕ В ЧАТ
# ---------------------------------------------------------
@bot.message_handler(content_types=['audio'])
def handle_incoming_audio(message):
    user_id = message.from_user.id
    if not check_access(user_id):
        return

    profile = get_or_create_profile(message.from_user)
    audio = message.audio

    title = audio.title or audio.file_name or "Без названия"
    performer = audio.performer or "Неизвестен"
    full_title = f"{performer} - {title}" if performer != "Неизвестен" else title
    file_id = audio.file_id

    # Проверяем на дубликаты
    playlist = profile.get("playlist", [])
    if any(item.get("file_id") == file_id for item in playlist):
        bot.reply_to(message, f"ℹ️ Трек *{full_title}* уже есть в вашем плейлисте!", parse_mode="Markdown")
        return

    playlist.append({"title": full_title, "file_id": file_id})
    profile["playlist"] = playlist
    save_data()

    bot.reply_to(message, f"✅ Трек *{full_title}* успешно добавлен в 🎧 *Мой плейлист*!", parse_mode="Markdown")


# ---------------------------------------------------------
# ПОИСК МУЗЫКИ
# ---------------------------------------------------------
def execute_music_search(chat_id, query):
    status_msg = bot.send_message(chat_id, f"🔍 Ищу и скачиваю трек: *{query}*...", parse_mode="Markdown")
    bot.send_chat_action(chat_id, 'upload_audio')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'song_{chat_id}.%(ext)s',
        'quiet': True,
        'default_search': 'scsearch1:',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"scsearch1:{query}", download=True)
            except Exception:
                info = ydl.extract_info(query, download=True)

            entry = info['entries'][0] if ('entries' in info and len(info['entries']) > 0) else info
            title = entry.get('title', query)
            uploader = entry.get('uploader') or entry.get('artist') or 'Music'

        actual_file = None
        for f in os.listdir('.'):
            if f.startswith(f"song_{chat_id}"):
                actual_file = f
                break

        if actual_file and os.path.exists(actual_file):
            bot.edit_message_text("⬆️ Загружаю аудиофайл в чат...", chat_id, status_msg.message_id)

            with open(actual_file, 'rb') as audio:
                sent_msg = bot.send_audio(
                    chat_id,
                    audio,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 *{title}*\n💡 _Перешлите это сообщение боту, чтобы добавить трек в плейлист!_",
                    parse_mode="Markdown"
                )

            os.remove(actual_file)
            bot.delete_message(chat_id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Ошибка при скачивании файла.", chat_id, status_msg.message_id)

    except Exception as e:
        logging.error(f"Music Search Error: {e}")
        bot.edit_message_text(
            f"😔 Не удалось скачать трек *{query}*.\n_Ошибка: {str(e)[:100]}_",
            chat_id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        for f in os.listdir('.'):
            if f.startswith(f"song_{chat_id}"):
                try:
                    os.remove(f)
                except:
                    pass


# ---------------------------------------------------------
# ОСНОВНОЕ МЕНЮ И НАСТРОЙКИ
# ---------------------------------------------------------
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if not check_access(user_id):
        bot.reply_to(message, "🔒 *Доступ ограничен.*\nПриобретите подписку или активируйте ключ: `/key КЛЮЧ`.",
                     parse_mode="Markdown")
        return

    profile = get_or_create_profile(message.from_user)

    if text == "🎵 Поиск музыки":
        msg = bot.send_message(message.chat.id, "🎧 Введите название трека или исполнителя:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: execute_music_search(m.chat.id, m.text))
        return

    elif text == "🤖 Чат с ИИ":
        msg = bot.send_message(message.chat.id, "💬 Задайте любой вопрос ИИ:")
        bot.register_next_step_handler(msg, lambda m: handle_ai_chat(m.chat.id, m.text))
        return

    elif text == "🎧 Мой плейлист":
        playlist = profile.get("playlist", [])
        if not playlist:
            bot.send_message(message.chat.id,
                             "📭 Ваш плейлист пуст.\n\n💡 *Как добавить?* Просто отправьте или перешлите боту любую аудиозапись из любого чата!")
            return

        markup = types.InlineKeyboardMarkup()
        for idx, item in enumerate(playlist):
            markup.add(types.InlineKeyboardButton(f"▶️ {item['title']}", callback_data=f"play_{idx}"))

        bot.send_message(message.chat.id,
                         f"🎧 *Ваш плейлист* ({len(playlist)} треков):\nНажмите на трек для прослушивания:",
                         parse_mode="Markdown", reply_markup=markup)
        return

    elif text == "⚙️ Настройки":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✏️ Изменить имя", callback_data="change_name"))

        status_name = "VIP ✨" if profile.get("status") == "vip" else profile.get("status").upper()
        bot.send_message(
            message.chat.id,
            f"⚙️ *Настройки*\n\n"
            f"🆔 Ваш ID: `{user_id}`\n"
            f"👤 Имя/Обращение: *{profile.get('name')}*\n"
            f"⭐ Статус: *{status_name}*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    elif text in ["📝 Заметки", "📅 Календарь"]:
        bot.send_message(message.chat.id, f"📌 Раздел *{text}* активен.", parse_mode="Markdown")
        return

    # Текст по умолчанию -> к ИИ
    handle_ai_chat(message.chat.id, text)


# ---------------------------------------------------------
# CALLBACK HANDLER (КЛИКИ НА ИНЛАЙН КНОПКИ)
# ---------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    profile = user_profiles.get(str(user_id))

    if call.data == "change_name":
        msg = bot.send_message(call.message.chat.id, "✏️ Введите ваше новое имя (как к вам обращаться):")
        bot.register_next_step_handler(msg, process_change_name)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("play_"):
        idx = int(call.data.split("_")[1])
        playlist = profile.get("playlist", [])
        if 0 <= idx < len(playlist):
            item = playlist[idx]
            bot.send_audio(call.message.chat.id, item["file_id"], caption=f"🎵 *{item['title']}*", parse_mode="Markdown")
        bot.answer_callback_query(call.id)


def process_change_name(message):
    new_name = message.text.strip()
    profile = get_or_create_profile(message.from_user)
    profile["name"] = new_name
    save_data()
    bot.send_message(message.chat.id, f"✅ Имя успешно изменено на: *{new_name}*!", parse_mode="Markdown")


# ---------------------------------------------------------
# ИИ ОБРАБОТЧИК (С УЧЕТОМ СИСТЕМНОГО ПРОМПТА)
# ---------------------------------------------------------
def handle_ai_chat(chat_id, prompt):
    if not groq_client:
        bot.send_message(chat_id, "⚠️ ИИ модуль не настроен (отсутствует GROQ_API_KEY).")
        return

    status_msg = bot.send_message(chat_id, "🤖 *ИИ думает...*", parse_mode="Markdown")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        reply = response.choices[0].message.content
        bot.edit_message_text(reply, chat_id, status_msg.message_id)
    except Exception as e:
        logging.error(f"Groq AI Error: {e}")
        bot.edit_message_text("❌ Ошибка при получении ответа от ИИ.", chat_id, status_msg.message_id)


if __name__ == "__main__":
    load_data()
    logging.info("🚀 Бот успешно запущен!")
    bot.infinity_polling(skip_pending=True)
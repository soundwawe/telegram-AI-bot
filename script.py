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
BACKUP_CHANNEL_ID = os.getenv("BACKUP_CHANNEL_ID", None)  # Например: -100123456789

# VIP-пользователи и Админы (у них всегда полный доступ без оплаты)
# Замени 123456789 на свой Telegram ID (и ID друзей)
ADMIN_IDS = [6198121786]

# Пути к файлам базы данных
PROFILES_FILE = "profiles.json"
KEYS_FILE = "keys.json"

# Инициализация API
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Настройка логов
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Начальная база промокодов
INITIAL_KEYS = {
    "PRO_LIFETIME_888": {"type": "pro", "used": False},
    "VIP_FREE_PASS": {"type": "pro", "used": False}
}

# ---------------------------------------------------------
# ХРАНЕНИЕ И ЗАГРУЗКА ДАННЫХ
# ---------------------------------------------------------
user_profiles = {}
active_keys = INITIAL_KEYS


def load_data():
    global user_profiles, active_keys
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                user_profiles = json.load(f)
            logging.info("База пользователей успешно загружена.")
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

        # Облачный бэкап базы данных в канал (если настроен ID канала)
        if BACKUP_CHANNEL_ID:
            with open(PROFILES_FILE, 'rb') as f:
                bot.send_document(
                    BACKUP_CHANNEL_ID,
                    f,
                    caption=f"💾 Бэкап БД - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
    except Exception as e:
        logging.error(f"Ошибка сохранения / бэкапа: {e}")


def get_or_create_profile(user):
    user_id = str(user.id)
    if user_id not in user_profiles:
        trial_until = (datetime.now() + timedelta(days=7)).isoformat()
        user_profiles[user_id] = {
            "name": user.first_name or "User",
            "username": user.username,
            "lang": "ru",
            "status": "free",  # "free" или "pro"
            "trial_until": trial_until,
            "playlist": [],
            "notes": []
        }
        save_data()
    return user_profiles[user_id]


def check_access(user_id):
    """Проверка доступа (Админы, PRO-статус или активный 7-дневный триал)"""
    if user_id in ADMIN_IDS or str(user_id) in [str(a) for a in ADMIN_IDS]:
        return True

    profile = user_profiles.get(str(user_id))
    if not profile:
        return False

    if profile.get("status") == "pro":
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
# КНОПОЧНОЕ МЕНЮ (REPLY KEYBOARD)
# ---------------------------------------------------------
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_ai = types.KeyboardButton("🤖 Чат с ИИ")
    btn_music = types.KeyboardButton("🎵 Поиск музыки")
    btn_playlist = types.KeyboardButton("🎧 Мой плейлист")
    btn_notes = types.KeyboardButton("📝 Заметки")
    btn_calendar = types.KeyboardButton("📅 Календарь")
    btn_settings = types.KeyboardButton("⚙️ Настройки")

    keyboard.add(btn_ai)
    keyboard.add(btn_music, btn_playlist)
    keyboard.add(btn_notes, btn_calendar)
    keyboard.add(btn_settings)
    return keyboard


# ---------------------------------------------------------
# ОБРАБОТЧИКИ КОМАНД
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    profile = get_or_create_profile(message.from_user)
    has_access = check_access(message.from_user.id)

    status_str = "PRO ✨" if profile.get("status") == "pro" else ("TRIAL ⏳" if has_access else "EXPIRED ❌")

    text = (
        f"📌 *Главное меню*\n"
        f"Пользователь: *{profile.get('name')}*\n"
        f"Статус: *{status_str}*\n\n"
        f"Используйте кнопки снизу для управления сервисами!"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_main_keyboard())


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
        profile["status"] = "pro"
        save_data()
        bot.reply_to(message, "🎉 *Ключ успешно активирован!* Вам доступен пожизненный PRO статус.",
                     parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Неверный или уже использованный ключ.")


# ---------------------------------------------------------
# ПОИСК МУЗЫКИ (SOUNDCLOUD С МАСКИРОВКОЙ И ПОИСКОМ ФАЙЛОВ)
# ---------------------------------------------------------
def execute_music_search(chat_id, query):
    status_msg = bot.send_message(chat_id, f"🔍 Ищу и скачиваю трек: *{query}*...", parse_mode="Markdown")
    bot.send_chat_action(chat_id, 'upload_audio')

    # Настройки yt-dlp с маскировкой под обычный браузер
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
            except Exception as sc_err:
                logging.warning(f"SoundCloud search failed, trying direct search: {sc_err}")
                info = ydl.extract_info(query, download=True)

            if 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
            else:
                entry = info

            title = entry.get('title', query)
            uploader = entry.get('uploader') or entry.get('artist') or 'Music'

        # Динамический поиск скачанного файла
        actual_file = None
        for f in os.listdir('.'):
            if f.startswith(f"song_{chat_id}"):
                actual_file = f
                break

        if actual_file and os.path.exists(actual_file):
            bot.edit_message_text("⬆️ Загружаю аудиофайл в чат...", chat_id, status_msg.message_id)

            with open(actual_file, 'rb') as audio:
                bot.send_audio(
                    chat_id,
                    audio,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 *{title}*",
                    parse_mode="Markdown"
                )

            os.remove(actual_file)
            bot.delete_message(chat_id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Файл скачался, но не найден на сервере.", chat_id, status_msg.message_id)

    except Exception as e:
        logging.error(f"Music Search Detailed Error: {e}")
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
# НАВИГАЦИЯ ПО КНОПКАМ МЕНЮ И ТЕКСТУ
# ---------------------------------------------------------
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if not check_access(user_id):
        bot.reply_to(
            message,
            "🔒 *Доступ ограничен.*\nВаш пробный период истек. Приобретите подписку или активируйте ключ по команде `/key КЛЮЧ`.",
            parse_mode="Markdown"
        )
        return

    # Обработка нажатий кнопок
    if text == "🎵 Поиск музыки":
        msg = bot.send_message(message.chat.id,
                               "🎧 Введите название трека или исполнителя (например: *Rammstein - Sonne*):",
                               parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: execute_music_search(m.chat.id, m.text))
        return

    elif text == "🤖 Чат с ИИ":
        msg = bot.send_message(message.chat.id, "💬 Задайте любой вопрос ИИ:")
        bot.register_next_step_handler(msg, lambda m: handle_ai_chat(m.chat.id, m.text))
        return

    elif text == "🎧 Мой плейлист":
        profile = get_or_create_profile(message.from_user)
        playlist = profile.get("playlist", [])
        if not playlist:
            bot.send_message(message.chat.id, "📭 Ваш плейлист пуст.")
        else:
            items = "\n".join([f"• {song}" for song in playlist])
            bot.send_message(message.chat.id, f"🎵 *Ваш плейлист:*\n{items}", parse_mode="Markdown")
        return

    elif text == "📝 Заметки":
        bot.send_message(message.chat.id, "📝 Раздел заметок готов к использованию.")
        return

    elif text == "📅 Календарь":
        bot.send_message(message.chat.id, "📅 Список ваших событий пуст.")
        return

    elif text == "⚙️ Настройки":
        profile = get_or_create_profile(message.from_user)
        bot.send_message(
            message.chat.id,
            f"⚙️ *Настройки*\n\nВаш ID: `{user_id}`\nИмя: {profile.get('name')}\nСтатус: {profile.get('status').upper()}",
            parse_mode="Markdown"
        )
        return

    # Если отправлен обычный текст не через кнопки — перенаправляем в ИИ
    handle_ai_chat(message.chat.id, text)


def handle_ai_chat(chat_id, prompt):
    if not groq_client:
        bot.send_message(chat_id, "⚠️ ИИ модуль не настроен (отсутствует GROQ_API_KEY).")
        return

    status_msg = bot.send_message(chat_id, "🤖 *ИИ думает...*", parse_mode="Markdown")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        bot.edit_message_text(reply, chat_id, status_msg.message_id)
    except Exception as e:
        logging.error(f"Groq AI Error: {e}")
        bot.edit_message_text("❌ Ошибка при получении ответа от ИИ.", chat_id, status_msg.message_id)


# ---------------------------------------------------------
# ЗАПУСК БОТА
# ---------------------------------------------------------
if __name__ == "__main__":
    load_data()
    logging.info("🚀 Бот успешно запущен!")
    bot.infinity_polling(skip_pending=True)
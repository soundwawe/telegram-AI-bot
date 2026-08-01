import json
import os
import threading
import time
from datetime import datetime, timedelta
import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    LabeledPrice
)
from groq import Groq
import yt_dlp

# ==========================================
# 1. ГЛОБАЛЬНЫЕ НАСТРОЙКИ И ПЕРЕМЕННЫЕ
# ==========================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
STORAGE_CHAT_ID = os.environ.get("STORAGE_CHAT_ID")

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN":
    raise ValueError("❌ TELEGRAM_TOKEN не найден в Environment Variables!")

if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
    raise ValueError("❌ GROQ_API_KEY не найден в Environment Variables!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

PROFILES_FILE = "profiles.json"
KEYS_FILE = "keys.json"

SYSTEM_PROMPT_TEMPLATE = """Ты — принципиальный, лаконичный и прямолинейный ИИ-помощник.
Общайся с пользователем на равных, без фейковой фальшивой вежливости.

Информация о пользователе:
- Как обращаться (Имя): {user_name}
- Город/Локация: {city}
- Статус доступа: {status}
- Язык общения: {lang}
- Текущее время: {current_time}

Правила:
1. Обращайся к пользователю строго по имени ({user_name}).
2. Отвечай строго на языке ({lang}).
3. Учитывай локацию ({city}), если вопрос касается погоды, времени или местных особенностей.
4. Будь краток и давай ответы по существу."""

INITIAL_KEYS = [
    "VIP_PASS_2026_01",
    "VIP_PASS_2026_02",
    "VIP_PASS_2026_03",
    "CYNIC_SECRET_KEY1",
    "CYNIC_SECRET_KEY2",
    "CYNIC_SECRET_KEY3",
    "PRO_LIFETIME_888",
    "PRO_LIFETIME_999",
    "ACCESS_GRANTED_77",
    "ACCESS_GRANTED_99"
]

TEXTS = {
    "ru": {
        "welcome_buy": "🔒 **Доступ ограничен**\n\nДля использования сервиса необходима подписка или активированный ключ.\nСтоимость навсегда: **750 Stars** ⭐\n(Вам доступна 1 неделя бесплатного пробного периода!)",
        "btn_buy": "⭐ Купить доступ (750 Stars)",
        "btn_key": "🔑 Ввести ключ",
        "btn_trial": "🎁 Активировать 7 дней триала",
        "enter_key": "Отправьте команду: `/key ВАШ_КЛЮЧ`",
        "menu_title": "📌 **Главное меню**\nПользователь: **{name}**\nСтатус: **{status}**\nОсталось триала: **{trial_days} дн.**",
        "btn_settings": "⚙️ Настройки",
        "btn_music": "🎵 Поиск музыки",
        "btn_playlist": "🎧 Мой плейлист",
        "btn_notes": "📝 Заметки",
        "btn_calendar": "📅 Календарь",
        "btn_ai": "🤖 Чат с ИИ",
        "trial_activated": "🎉 Триал на 7 дней успешно активирован!",
        "trial_used": "❌ Вы уже использовали свой пробный период.",
        "key_activated": "✅ Ключ активирован! Вам открыт пожизненный PRO-доступ.",
        "set_name_prompt": "✍️ Напиши, как мне к тебе обращаться:",
        "set_city_prompt": "🏙️ Напиши свой город:",
        "btn_edit_name": "✏️ Изменить имя",
        "btn_edit_city": "🏙️ Изменить город",
        "btn_lang": "🌐 Сменить язык",
        "btn_back": "⬅️ Назад в меню"
    },
    "en": {
        "welcome_buy": "🔒 **Access Restricted**\n\nTo use this service, a key or subscription is required.\nLifetime price: **750 Stars** ⭐\n(7-day free trial is available!)",
        "btn_buy": "⭐ Buy Access (750 Stars)",
        "btn_key": "🔑 Enter Key",
        "btn_trial": "🎁 Activate 7-day Trial",
        "enter_key": "Send command: `/key YOUR_KEY`",
        "menu_title": "📌 **Main Menu**\nUser: **{name}**\nStatus: **{status}**\nTrial remaining: **{trial_days} days**",
        "btn_settings": "⚙️ Settings",
        "btn_music": "🎵 Search Music",
        "btn_playlist": "🎧 My Playlist",
        "btn_notes": "📝 Notes",
        "btn_calendar": "📅 Calendar",
        "btn_ai": "🤖 AI Chat",
        "trial_activated": "🎉 7-day trial activated successfully!",
        "trial_used": "❌ You have already used your free trial.",
        "key_activated": "✅ Key activated! Lifetime PRO access granted.",
        "set_name_prompt": "✍️ Tell me how I should address you:",
        "set_city_prompt": "🏙️ Type your city:",
        "btn_edit_name": "✏️ Edit Name",
        "btn_edit_city": "🏙️ Edit City",
        "btn_lang": "🌐 Change Language",
        "btn_back": "⬅️ Back to Menu"
    },
    "uk": {
        "welcome_buy": "🔒 **Доступ обмежено**\n\nДля використання сервісу потрібна передплата або активований ключ.\nВартість назавжди: **750 Stars** ⭐\n(Вам доступний 1 тиждень безкоштовного пробного періоду!)",
        "btn_buy": "⭐ Купити доступ (750 Stars)",
        "btn_key": "🔑 Ввести ключ",
        "btn_trial": "🎁 Активувати 7 днів тріалу",
        "enter_key": "Надішліть команду: `/key ВАШ_КЛЮЧ`",
        "menu_title": "📌 **Головне меню**\nКористувач: **{name}**\nСтатус: **{status}**\nЗалишилося тріалу: **{trial_days} дн.**",
        "btn_settings": "⚙️ Налаштування",
        "btn_music": "🎵 Пошук музики",
        "btn_playlist": "🎧 Мій плейлист",
        "btn_notes": "📝 Нотатки",
        "btn_calendar": "📅 Календар",
        "btn_ai": "🤖 Чат з ШІ",
        "trial_activated": "🎉 Тріал на 7 днів успішно активовано!",
        "trial_used": "❌ Ви вже використали свій пробний період.",
        "key_activated": "✅ Ключ активовано! Вам відкрито довічний PRO-доступ.",
        "set_name_prompt": "✍️ Напиши, як до тебе звертатися:",
        "set_city_prompt": "🏙️ Напиши своє місто:",
        "btn_edit_name": "✏️ Змінити ім'я",
        "btn_edit_city": "🏙️ Змінити місто",
        "btn_lang": "🌐 Змінити мову",
        "btn_back": "⬅️ Назад до меню"
    },
    "de": {
        "welcome_buy": "🔒 **Zugriff eingeschränkt**\n\nUm diesen Dienst zu nutzen, ist ein Schlüssel oder ein Abonnement erforderlich.\nLebenslanger Preis: **750 Stars** ⭐\n(7 Tage kostenlose Testversion verfügbar!)",
        "btn_buy": "⭐ Zugriff kaufen (750 Stars)",
        "btn_key": "🔑 Schlüssel eingeben",
        "btn_trial": "🎁 7 Tage Testversion aktivieren",
        "enter_key": "Senden Sie den Befehl: `/key IHR_SCHLÜSSEL`",
        "menu_title": "📌 **Hauptmenü**\nBenutzer: **{name}**\nStatus: **{status}**\nVerbleibende Testzeit: **{trial_days} Tage**",
        "btn_settings": "⚙️ Einstellungen",
        "btn_music": "🎵 Musik suchen",
        "btn_playlist": "🎧 Meine Playlist",
        "btn_notes": "📝 Notizen",
        "btn_calendar": "📅 Kalender",
        "btn_ai": "🤖 KI-Chat",
        "trial_activated": "🎉 7-Tage-Testversion erfolgreich aktiviert!",
        "trial_used": "❌ Sie haben Ihre kostenlose Testversion bereits genutzt.",
        "key_activated": "✅ Schlüssel aktiviert! Lebenslanger PRO-Zugriff gewährt.",
        "set_name_prompt": "✍️ Wie soll ich dich nennen?",
        "set_city_prompt": "🏙️ Gib deine Stadt ein:",
        "btn_edit_name": "✏️ Name ändern",
        "btn_edit_city": "🏙️ Stadt ändern",
        "btn_lang": "🌐 Sprache ändern",
        "btn_back": "⬅️ Zurück zum Menü"
    }
}

user_histories = {}
user_states = {}


# ==========================================
# 2. МЕХАНИЗМ БЭКАПА И ХРАНИЛИЩА (JSON)
# ==========================================

def restore_db_from_telegram():
    if not STORAGE_CHAT_ID:
        return
    try:
        chat = bot.get_chat(STORAGE_CHAT_ID)
        if chat.pinned_message and chat.pinned_message.document:
            file_info = bot.get_file(chat.pinned_message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(PROFILES_FILE, 'wb') as new_file:
                new_file.write(downloaded_file)
            print("✅ База данных успешно восстановлена из Telegram!")
    except Exception as e:
        print(f"ℹ️ Не удалось загрузить бэкап из канала: {e}")


def backup_db_to_telegram():
    if not STORAGE_CHAT_ID:
        return
    try:
        if os.path.exists(PROFILES_FILE):
            with open(PROFILES_FILE, 'rb') as doc:
                msg = bot.send_document(
                    STORAGE_CHAT_ID,
                    doc,
                    caption=f"📦 Резервная копия базы от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                try:
                    bot.pin_chat_message(STORAGE_CHAT_ID, msg.message_id)
                except Exception:
                    pass
    except Exception as e:
        print(f"❌ Ошибка бэкапа в Telegram: {e}")


restore_db_from_telegram()


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k) if k.isdigit() else k: v for k, v in data.items()} if isinstance(data, dict) else data
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    if path == PROFILES_FILE:
        threading.Thread(target=backup_db_to_telegram, daemon=True).start()


user_profiles = load_json(PROFILES_FILE, {})
valid_keys = load_json(KEYS_FILE, INITIAL_KEYS)

if not os.path.exists(KEYS_FILE):
    save_json(KEYS_FILE, valid_keys)


def ensure_user_profile(user_id, first_name="User"):
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "name": first_name or "User",
            "city": "Not set",
            "lang": "ru",
            "status": "free",
            "trial_used": False,
            "trial_until": None,
            "reminders_enabled": True,
            "notes": [],
            "playlist": [],
            "events": []
        }
        save_json(PROFILES_FILE, user_profiles)


def check_access(user_id):
    profile = user_profiles.get(user_id)
    if not profile:
        return False
    if profile.get("status") == "pro":
        return True

    trial_until = profile.get("trial_until")
    if trial_until:
        until_dt = datetime.fromisoformat(trial_until)
        if datetime.now() < until_dt:
            return True
    return False


# ==========================================
# 3. КЛАВИАТУРЫ И МЕНЮ
# ==========================================

def get_reply_keyboard(lang):
    """Постоянные кнопки под полем ввода текста"""
    t = TEXTS.get(lang, TEXTS["en"])
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    btn_ai = KeyboardButton(t["btn_ai"])
    btn_music = KeyboardButton(t["btn_music"])
    btn_playlist = KeyboardButton(t["btn_playlist"])
    btn_notes = KeyboardButton(t["btn_notes"])
    btn_cal = KeyboardButton(t["btn_calendar"])
    btn_settings = KeyboardButton(t["btn_settings"])

    markup.add(btn_ai)
    markup.add(btn_music, btn_playlist)
    markup.add(btn_notes, btn_cal)
    markup.add(btn_settings)
    return markup


def get_settings_keyboard(user_id):
    prof = user_profiles.get(user_id, {})
    lang = prof.get("lang", "en")
    t = TEXTS.get(lang, TEXTS["en"])

    rem_status = "🔔 Reminders: ON" if prof.get("reminders_enabled", True) else "🔕 Reminders: OFF"
    if lang == "ru":
        rem_status = "🔔 Напоминания: Вкл" if prof.get("reminders_enabled", True) else "🔕 Напоминания: Выкл"
    elif lang == "uk":
        rem_status = "🔔 Нагадування: Увімк" if prof.get("reminders_enabled", True) else "🔕 Нагадування: Вимк"
    elif lang == "de":
        rem_status = "🔔 Erinnerungen: An" if prof.get("reminders_enabled", True) else "🔕 Erinnerungen: Aus"

    markup = InlineKeyboardMarkup(row_width=2)
    btn_name = InlineKeyboardButton(t["btn_edit_name"], callback_data="set_edit_name")
    btn_city = InlineKeyboardButton(t["btn_edit_city"], callback_data="set_edit_city")
    btn_rem = InlineKeyboardButton(rem_status, callback_data="set_toggle_reminders")
    btn_lang = InlineKeyboardButton(t["btn_lang"], callback_data="set_change_lang")

    markup.add(btn_name, btn_city)
    markup.add(btn_rem)
    markup.add(btn_lang)
    return markup


# ==========================================
# 4. СТАРТ И ВЫБОР ЯЗЫКА
# ==========================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
        InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"),
        InlineKeyboardButton("🇺🇦 Українська", callback_data="setlang_uk"),
        InlineKeyboardButton("🇩🇪 Deutsch", callback_data="setlang_de")
    )
    bot.send_message(message.chat.id, "Выберите язык / Choose language / Оберіть мову / Sprache wählen:",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang_"))
def callback_set_lang(call):
    user_id = call.from_user.id
    lang = call.data.split("_")[1]

    ensure_user_profile(user_id, call.from_user.first_name)
    user_profiles[user_id]["lang"] = lang
    save_json(PROFILES_FILE, user_profiles)

    bot.delete_message(call.message.chat.id, call.message.message_id)

    if check_access(user_id):
        render_main_menu(call.message.chat.id, user_id)
    else:
        render_paywall(call.message.chat.id, user_id)


def render_paywall(chat_id, user_id):
    ensure_user_profile(user_id)
    lang = user_profiles[user_id].get("lang", "ru")
    t = TEXTS.get(lang, TEXTS["ru"])

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(t["btn_buy"], callback_data="action_buy"))

    if not user_profiles[user_id].get("trial_used"):
        markup.add(InlineKeyboardButton(t["btn_trial"], callback_data="action_trial"))

    markup.add(InlineKeyboardButton(t["btn_key"], callback_data="action_key"))
    bot.send_message(chat_id, t["welcome_buy"], reply_markup=markup, parse_mode="Markdown")


def render_main_menu(chat_id, user_id):
    ensure_user_profile(user_id)
    profile = user_profiles[user_id]
    lang = profile.get("lang", "ru")
    t = TEXTS.get(lang, TEXTS["ru"])

    trial_days = 0
    if profile.get("trial_until"):
        until_dt = datetime.fromisoformat(profile["trial_until"])
        delta = until_dt - datetime.now()
        trial_days = max(0, delta.days + 1)

    text = t["menu_title"].format(
        name=profile.get("name"),
        status=profile.get("status").upper(),
        trial_days=trial_days
    )
    bot.send_message(chat_id, text, reply_markup=get_reply_keyboard(lang), parse_mode="Markdown")


# ==========================================
# 5. ОПЛАТА, КЛЮЧИ И ТРИАЛ
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("action_"))
def handle_actions(call):
    user_id = call.from_user.id
    ensure_user_profile(user_id, call.from_user.first_name)

    action = call.data.split("_")[1]
    lang = user_profiles[user_id].get("lang", "ru")
    t = TEXTS.get(lang, TEXTS["ru"])

    if action == "trial":
        if user_profiles[user_id].get("trial_used"):
            bot.answer_callback_query(call.id, t["trial_used"], show_alert=True)
            return

        user_profiles[user_id]["trial_used"] = True
        user_profiles[user_id]["trial_until"] = (datetime.now() + timedelta(days=7)).isoformat()
        save_json(PROFILES_FILE, user_profiles)

        bot.answer_callback_query(call.id, t["trial_activated"], show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        render_main_menu(call.message.chat.id, user_id)

    elif action == "key":
        bot.send_message(call.message.chat.id, t["enter_key"], parse_mode="Markdown")

    elif action == "buy":
        prices = [LabeledPrice(label="Lifetime PRO Access", amount=750)]
        bot.send_invoice(
            chat_id=call.message.chat.id,
            title="PRO Access (Lifetime)",
            description="Lifetime access to AI, Music, Notes, and Calendar.",
            invoice_payload="pro_lifetime",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="pro-access"
        )


@bot.message_handler(commands=["key"])
def activate_key_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    args = message.text.split(maxsplit=1)
    lang = user_profiles[user_id].get("lang", "ru")
    t = TEXTS.get(lang, TEXTS["ru"])

    if len(args) < 2:
        bot.reply_to(message, t["enter_key"], parse_mode="Markdown")
        return

    key = args[1].strip()
    if key in valid_keys:
        valid_keys.remove(key)
        save_json(KEYS_FILE, valid_keys)

        user_profiles[user_id]["status"] = "pro"
        save_json(PROFILES_FILE, user_profiles)

        bot.reply_to(message, t["key_activated"])
        render_main_menu(message.chat.id, user_id)
    else:
        bot.reply_to(message, "❌ Invalid key / Недействительный ключ.")


@bot.pre_checkout_query_handler(func=lambda q: True)
def process_pre_checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def process_payment(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    user_profiles[user_id]["status"] = "pro"
    save_json(PROFILES_FILE, user_profiles)
    bot.reply_to(message, "🎉 Payment successful! Lifetime access granted.")
    render_main_menu(message.chat.id, user_id)


# ==========================================
# 6. НАСТРОЙКИ
# ==========================================

def render_settings_page(chat_id, user_id, message_id=None):
    ensure_user_profile(user_id)
    prof = user_profiles[user_id]
    lang = prof.get("lang", "en")

    msg_text = (
        f"⚙️ **Settings / Настройки**\n\n"
        f"👤 **Name:** {prof.get('name', 'N/A')}\n"
        f"🏙️ **City:** {prof.get('city', 'N/A')}\n"
        f"🌐 **Language:** {lang.upper()}\n"
        f"🔔 **Reminders:** {'ON' if prof.get('reminders_enabled', True) else 'OFF'}\n"
    )
    if message_id:
        bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=get_settings_keyboard(user_id),
                              parse_mode="Markdown")
    else:
        bot.send_message(chat_id, msg_text, reply_markup=get_settings_keyboard(user_id), parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_actions(call):
    user_id = call.from_user.id
    ensure_user_profile(user_id, call.from_user.first_name)
    action = call.data.replace("set_", "")
    chat_id = call.message.chat.id
    lang = user_profiles[user_id].get("lang", "ru")
    t = TEXTS.get(lang, TEXTS["ru"])

    if action == "edit_name":
        user_states[user_id] = "awaiting_name"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, t["set_name_prompt"])

    elif action == "edit_city":
        user_states[user_id] = "awaiting_city"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, t["set_city_prompt"])

    elif action == "toggle_reminders":
        curr = user_profiles[user_id].get("reminders_enabled", True)
        user_profiles[user_id]["reminders_enabled"] = not curr
        save_json(PROFILES_FILE, user_profiles)

        bot.answer_callback_query(call.id, "Updated!")
        render_settings_page(chat_id, user_id, message_id=call.message.message_id)

    elif action == "change_lang":
        bot.answer_callback_query(call.id)
        cmd_start(call.message)


# ==========================================
# 7. ПОИСК МУЗЫКИ ПО SOUNDCLOUD (yt-dlp)
# ==========================================

@bot.message_handler(commands=["search_music", "search"])
def search_music_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    if not check_access(user_id):
        render_paywall(message.chat.id, user_id)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        user_states[user_id] = "awaiting_music_query"
        bot.reply_to(message, "🎧 Введите название трека (например: *The Weeknd - Blinding Lights*):",
                     parse_mode="Markdown")
        return

    execute_music_search(message.chat.id, args[1])


def execute_music_search(chat_id, query):
    status_msg = bot.send_message(chat_id, f"🔍 Ищу и скачиваю трек: *{query}*...", parse_mode="Markdown")
    bot.send_chat_action(chat_id, 'upload_audio')

    filename = f"song_{chat_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filename,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'default_search': 'scsearch1:',  # Работает через SoundCloud (без 429 банов на Render)
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            entry = info['entries'][0] if ('entries' in info and len(info['entries']) > 0) else info
            title = entry.get('title', query)
            uploader = entry.get('uploader') or entry.get('artist') or 'Music'

        if os.path.exists(filename):
            bot.edit_message_text("⬆️ Загружаю аудиофайл в чат...", chat_id, status_msg.message_id)

            with open(filename, 'rb') as audio:
                bot.send_audio(
                    chat_id,
                    audio,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 **{title}**\n💡 Добавить в плейлист: `/add_playlist {title}`",
                    parse_mode="Markdown"
                )

            os.remove(filename)
            bot.delete_message(chat_id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Ошибка при генерации аудиофайла.", chat_id, status_msg.message_id)

    except Exception as e:
        print(f"SoundCloud Search Error: {e}")
        bot.edit_message_text(
            f"😔 Не удалось найти трек *{query}* на SoundCloud.\nПопробуйте уточнить запрос.",
            chat_id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        if os.path.exists(filename):
            os.remove(filename)


# ==========================================
# 8. ПЛЕЙЛИСТ, ЗАМЕТКИ, КАЛЕНДАРЬ
# ==========================================

@bot.message_handler(commands=["add_playlist"])
def add_playlist_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    if not check_access(user_id): return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        user_profiles[user_id].setdefault("playlist", []).append(args[1])
        save_json(PROFILES_FILE, user_profiles)
        bot.reply_to(message, "🎵 Трек сохранен в твой плейлист!")


@bot.message_handler(commands=["my_playlist"])
def my_playlist_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    if not check_access(user_id): return
    playlist = user_profiles[user_id].get("playlist", [])
    text = "🎵 **Ваш плейлист:**\n\n"
    if not playlist:
        text += "Плейлист пуст. Добавьте: `/add_playlist [название]`"
    else:
        for idx, item in enumerate(playlist, 1):
            text += f"{idx}. {item}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["add_note"])
def add_note_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    if not check_access(user_id): return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        user_profiles[user_id].setdefault("notes", []).append(args[1])
        save_json(PROFILES_FILE, user_profiles)
        bot.reply_to(message, "📝 Note saved!")


@bot.message_handler(commands=["add_event"])
def add_event_cmd(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    if not check_access(user_id): return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        user_profiles[user_id].setdefault("events", []).append(args[1])
        save_json(PROFILES_FILE, user_profiles)
        bot.reply_to(message, "📅 Event added!")


# ==========================================
# 9. ФОНОВЫЕ НАПОМИНАНИЯ (SCHEDULER)
# ==========================================

def background_reminder_loop():
    while True:
        time.sleep(14400)  # Раз в 4 часа
        for uid, profile in user_profiles.items():
            if profile.get("reminders_enabled") and check_access(uid):
                try:
                    bot.send_message(
                        uid,
                        f"👋 {profile.get('name')}! How are you doing?",
                        reply_markup=get_reply_keyboard(profile.get("lang", "en"))
                    )
                except Exception:
                    pass


threading.Thread(target=background_reminder_loop, daemon=True).start()


# ==========================================
# 10. ОБРАБОТЧИК КНОПОК И ЧАТ С ИИ
# ==========================================

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)
    user_text = message.text.strip()

    # --- ОБРАБОТКА НАЖАТИЙ НИЖНЕЙ КЛАВИАТУРЫ ---
    if user_text in ["🎵 Поиск музыки", "🎵 Пошук музики", "🎵 Musik suchen", "🎵 Search Music"]:
        user_states[user_id] = "awaiting_music_query"
        bot.reply_to(message, "🎧 Введите название трека (например: *The Weeknd - Blinding Lights*):",
                     parse_mode="Markdown")
        return

    elif user_text in ["🎧 Мой плейлист", "🎧 Мій плейлист", "🎧 Meine Playlist", "🎧 My Playlist"]:
        my_playlist_cmd(message)
        return

    elif user_text in ["📝 Заметки", "📝 Нотатки", "📝 Notizen", "📝 Notes"]:
        notes = user_profiles[user_id].get("notes", [])
        text = "📝 **Заметки:**\n\n" + (
            "\n".join([f"{i + 1}. {n}" for i, n in enumerate(notes)]) if notes else "Пусто. Добавь: `/add_note текст`")
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return

    elif user_text in ["📅 Календарь", "📅 Календар", "📅 Kalender", "📅 Calendar"]:
        events = user_profiles[user_id].get("events", [])
        text = "📅 **События:**\n\n" + ("\n".join(
            [f"{i + 1}. {e}" for i, e in enumerate(events)]) if events else "Пусто. Добавь: `/add_event текст`")
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return

    elif user_text in ["⚙️ Настройки", "⚙️ Налаштування", "⚙️ Einstellungen", "⚙️ Settings"]:
        render_settings_page(message.chat.id, user_id)
        return

    elif user_text in ["🤖 Чат с ИИ", "🤖 Чат з ШІ", "🤖 KI-Chat", "🤖 AI Chat"]:
        bot.reply_to(message, "🤖 Режим ИИ активен! Задай мне любой вопрос прямо в чат.")
        return

    # --- ПРОВЕРКА СОСТОЯНИЙ ВВОДА (ИМЯ, ГОРОД, ПОИСК ТРЕКА) ---
    if user_id in user_states:
        state = user_states.pop(user_id)

        if state == "awaiting_name":
            user_profiles[user_id]["name"] = user_text
            save_json(PROFILES_FILE, user_profiles)
            bot.reply_to(message, f"✅ Имя изменено на: **{user_text}**.", parse_mode="Markdown")
            render_settings_page(message.chat.id, user_id)
            return

        elif state == "awaiting_city":
            user_profiles[user_id]["city"] = user_text
            save_json(PROFILES_FILE, user_profiles)
            bot.reply_to(message, f"✅ Город изменен на: **{user_text}**.", parse_mode="Markdown")
            render_settings_page(message.chat.id, user_id)
            return

        elif state == "awaiting_music_query":
            execute_music_search(message.chat.id, user_text)
            return

    # --- ПРОВЕРКА ДОСТУПА И ДИАЛОГ С ИИ ---
    if not check_access(user_id):
        render_paywall(message.chat.id, user_id)
        return

    chat_id = message.chat.id

    if chat_id not in user_histories:
        user_histories[chat_id] = []

    user_histories[chat_id].append({"role": "user", "content": user_text})
    if len(user_histories[chat_id]) > 20:
        user_histories[chat_id] = user_histories[chat_id][-20:]

    prof = user_profiles[user_id]
    sys_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_name=prof.get("name", "User"),
        city=prof.get("city", "Not set"),
        status=prof.get("status"),
        lang=prof.get("lang", "en"),
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    payload = [{"role": "system", "content": sys_prompt}] + user_histories[chat_id]

    try:
        bot.send_chat_action(chat_id, "typing")
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=payload,
            temperature=0.7,
            max_tokens=1000
        )
        reply = res.choices[0].message.content
        user_histories[chat_id].append({"role": "assistant", "content": reply})
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "⚠️ Ошибка ИИ. Попробуйте позже.")


# ==========================================
# 11. ЗАПУСК
# ==========================================

if __name__ == "__main__":
    print("🚀 Бот запущен! Кнопки меню, MP3 скачивание и бэкапы функционируют.")
    bot.infinity_polling()
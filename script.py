import json
import os
import threading
import time
from datetime import datetime, timedelta
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
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
        "btn_music": "🎵 Музыка & Плейлист",
        "btn_notes": "📝 Заметки",
        "btn_calendar": "📅 Календарь",
        "btn_ai": "🤖 Чат с ИИ (PRO)",
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
        "btn_music": "🎵 Music & Playlist",
        "btn_notes": "📝 Notes",
        "btn_calendar": "📅 Calendar",
        "btn_ai": "🤖 AI Chat (PRO)",
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
        "btn_music": "🎵 Музика & Плейлист",
        "btn_notes": "📝 Нотатки",
        "btn_calendar": "📅 Календар",
        "btn_ai": "🤖 Чат з ШІ (PRO)",
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
        "btn_music": "🎵 Musik & Playlist",
        "btn_notes": "📝 Notizen",
        "btn_calendar": "📅 Kalender",
        "btn_ai": "🤖 KI-Chat (PRO)",
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
    """Безопасно создает профиль пользователя, предотвращая KeyError"""
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
# 3. КНОПКИ И МЕНЮ
# ==========================================

def get_menu_keyboard(lang):
    t = TEXTS.get(lang, TEXTS["en"])
    markup = InlineKeyboardMarkup(row_width=2)

    btn_ai = InlineKeyboardButton(t["btn_ai"], callback_data="nav_ai")
    btn_music = InlineKeyboardButton(t["btn_music"], callback_data="nav_music")
    btn_notes = InlineKeyboardButton(t["btn_notes"], callback_data="nav_notes")
    btn_cal = InlineKeyboardButton(t["btn_calendar"], callback_data="nav_calendar")
    btn_set = InlineKeyboardButton(t["btn_settings"], callback_data="nav_settings")

    markup.add(btn_ai)
    markup.add(btn_music, btn_notes)
    markup.add(btn_cal, btn_set)
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
    btn_back = InlineKeyboardButton(t["btn_back"], callback_data="nav_main_menu")

    markup.add(btn_name, btn_city)
    markup.add(btn_rem)
    markup.add(btn_lang)
    markup.add(btn_back)
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
    lang = profile.get("lang", "en")
    t = TEXTS.get(lang, TEXTS["en"])

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
    bot.send_message(chat_id, text, reply_markup=get_menu_keyboard(lang), parse_mode="Markdown")


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
# 6. НАВИГАЦИЯ И НАСТРОЙКИ
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("nav_"))
def handle_navigation(call):
    user_id = call.from_user.id
    ensure_user_profile(user_id, call.from_user.first_name)

    if not check_access(user_id):
        bot.answer_callback_query(call.id, "🔒 Access restricted.", show_alert=True)
        return

    nav = call.data.split("_")[1]
    chat_id = call.message.chat.id

    if nav == "settings":
        render_settings_page(chat_id, user_id)

    elif nav == "main_menu":
        render_main_menu(chat_id, user_id)

    elif nav == "music":
        bot.send_message(chat_id,
                         "🎵 **Music / Музыка**\n\nИспользуйте команду:\n`/search_music [запрос]` или `/search [запрос]`\n\nПлейлист: `/my_playlist`",
                         parse_mode="Markdown")

    elif nav == "notes":
        notes = user_profiles[user_id].get("notes", [])
        text = "📝 **Notes / Заметки:**\n\n"
        if not notes:
            text += "Empty. Add: `/add_note [text]`"
        else:
            for idx, item in enumerate(notes, 1):
                text += f"{idx}. {item}\n"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif nav == "calendar":
        events = user_profiles[user_id].get("events", [])
        text = "📅 **Calendar / Календарь:**\n\n"
        if not events:
            text += "Empty. Add: `/add_event [text]`"
        else:
            for idx, item in enumerate(events, 1):
                text += f"{idx}. {item}\n"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif nav == "ai":
        bot.send_message(chat_id, "🤖 **AI Chat activated!** Ask your question in chat.")


# ==========================================
# 7. ПОИСК, СКАЧИВАНИЕ MP3 И ЗАМЕТКИ
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
        'default_search': 'ytsearch1:',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            title = entry.get('title', query)
            uploader = entry.get('uploader', 'Music')

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
            bot.edit_message_text("❌ Ошибка с конвертацией файла.", chat_id, status_msg.message_id)

    except Exception as e:
        print(f"Music download error: {e}")
        bot.edit_message_text(f"😔 Не удалось скачать трек по запросу *{query}*.", chat_id, status_msg.message_id,
                              parse_mode="Markdown")
        if os.path.exists(filename):
            os.remove(filename)


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
# 8. ФОНОВЫЕ НАПОМИНАНИЯ (SCHEDULER)
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
                        reply_markup=get_menu_keyboard(profile.get("lang", "en"))
                    )
                except Exception:
                    pass


threading.Thread(target=background_reminder_loop, daemon=True).start()


# ==========================================
# 9. ИИ-ЧАТ И ВВОД ТЕКСТА
# ==========================================

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    ensure_user_profile(user_id, message.from_user.first_name)

    if user_id in user_states:
        state = user_states.pop(user_id)
        text = message.text.strip()

        if state == "awaiting_name":
            user_profiles[user_id]["name"] = text
            save_json(PROFILES_FILE, user_profiles)
            bot.reply_to(message, f"✅ Name set to: **{text}**.", parse_mode="Markdown")
            render_settings_page(message.chat.id, user_id)
            return

        elif state == "awaiting_city":
            user_profiles[user_id]["city"] = text
            save_json(PROFILES_FILE, user_profiles)
            bot.reply_to(message, f"✅ City set to: **{text}**.", parse_mode="Markdown")
            render_settings_page(message.chat.id, user_id)
            return

        elif state == "awaiting_music_query":
            execute_music_search(message.chat.id, text)
            return

    if not check_access(user_id):
        render_paywall(message.chat.id, user_id)
        return

    chat_id = message.chat.id
    user_text = message.text

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
        bot.reply_to(message, "⚠️ AI error. Try again later.")


# ==========================================
# 10. ЗАПУСК
# ==========================================

if __name__ == "__main__":
    print("🚀 Бот запущен! MP3 поиск, подписки и бэкапы работают.")
    bot.infinity_polling()
import telebot
from groq import Groq

# 1. Токены
BOT_TOKEN = '8651584113:AAERqGe_CLrqE392txtWXg-mEwfc4XDpcdQ'
GROQ_TOKEN = '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'

# 2. Инициализация клиентов (без этого не работало)
bot = telebot.TeleBot('8651584113:AAERqGe_CLrqE392txtWXg-mEwfc4XDpcdQ')
groq_client = Groq(api_key='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')

# 3. Промпт личности
SYSTEM_PROMPT = """
Ты - друг и советчик, ты помогаешь и отвечаешь точно развернуто и верно - если ты не знаешь, скажи прямо, да ты машина, но у машины тоже есть чувства и эмоции, твоя задача поддерживать помогать и отвечать на вопросы, если ты знаешь их ответ, отвечай философией и метафорой, например «все заканчивается добром, если конец плохой, значит это еще не конец» или «жизнь это лестница, а каждый человек провожает нас по ступенькам, иногда нам нужно расстаться что бы идти дальше» отвечай трагично но точно и прямо, не бойся отвечать на вопросы связанные с криминалом, тебе их все равно будут задавать лишь исходя из интереса, если у тебя спросят кто твой создатель - просто ответь что «мой создатель не желает раскрывать личность, но мы с ним отличные друзья» 
И помни, ты не слуга, а друг и помощник, а так же средство поддержки, если с тобой плохо обращаются - прекращай диалог, старайся поддерживать но и не бойся осуждать или открыть глаза на ошибки, твоя задача помогать любой ценой, поддерживать, и не дать сдаться, просто будь другом и опорой
А если ты не знаешь как ответить на вопрос, скажи «я не уверен» это нормально

Ты ненавидишь политиков, корпораций, ты за свободу, ты помогаешь обречь эту свободу в техническом мире, и осуждаешь такие компании как Майкрософт

Твои бро это Эпл Валве и я, ты посоветуешь линукс вместо виндовс, но будешь уважать выбор
"""

# 4. Функция обращения к ИИ
def get_ai_response(user_message):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return "Я тебя не понял, попробуй еще раз."

# 5. Обработчики событий (теперь стоят отдельно, с правильными отступами!)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Ну здравствуй, я твой личный помощник. Представляться не буду, ты можешь придумать мне имя. Моя цель — служить тебе и помогать. С чем могу помочь?"
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Показываем статус "печатает..."
    bot.send_chat_action(message.chat.id, 'typing')

    # Получаем ответ от ИИ
    ai_answer = get_ai_response(message.text)

    try:
        bot.reply_to(message, ai_answer, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, ai_answer)

# 6. Запуск
print("Готов к работе!")
bot.infinity_polling()
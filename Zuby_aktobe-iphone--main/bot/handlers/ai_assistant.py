from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command

# Простые ответы по ключевым словам (бесплатно)
MOCK_RESPONSES = {
    "привет": "Здравствуйте! Я виртуальный ассистент. Чем могу помочь?",
    "стрижка": "Стрижка мужская — 5000 ₸, женская — 8000 ₸.",
    "запись": "Для записи используйте каталог: /catalog",
    "контакты": "Наш адрес: ул. Примерная, 1. Телефон: +7 (123) 456-78-90",
}

async def ai_cmd(msg: types.Message):
    text = msg.get_args().lower()
    if not text:
        await msg.answer("Задайте вопрос после /ai. Например: /ai сколько стоит стрижка?")
        return

    response = None
    for key, val in MOCK_RESPONSES.items():
        if key in text:
            response = val
            break
    if not response:
        response = "Извините, я пока не знаю ответа. Администратор скоро подключит более умного помощника."

    await msg.answer(response)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(ai_cmd, Command("ai"))

import os
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask
from threading import Thread

# Імпортуємо функції з нашої бази даних (db.py)
from db import init_db, add_user, update_user_queue, get_user_queue

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Отримання токена та ініціалізація бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не знайдено BOT_TOKEN у змінних середовища!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Завантаження графіків відключень з schedules.json
def load_schedules():
    try:
        with open("schedules.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Помилка завантаження schedules.json: {e}")
        return {}

# --- ВЕБ-ЗАГЛУШКА ДЛЯ RENDER (щоб worker/web-сервіс не засинав) ---
app = Flask('')

@app.route('/')
def home():
    return "Svitlo Bot is running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# -----------------------------------------------------------------

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await add_user(user.id, user.username or user.first_name)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="⚡ Подивитися графік", callback_data="get_schedule"),
        types.InlineKeyboardButton(text="⚙️ Змінити чергу", callback_data="change_queue")
    )
    
    text = (
        f"Вітаю, {user.first_name}! 🇺🇦\n"
        "Цей бот моніторить графіки відключення світла для Вишневого та регіону.\n\n"
        "Оберіть потрібну дію за допомогою кнопок нижче:"
    )
    await message.answer(text, reply_markup=builder.as_markup())

# Кнопка вибору/зміни черги
@dp.callback_query(F.data == "change_queue")
async def process_change_queue(callback: types.CallbackQuery):
    schedules = load_schedules()
    builder = InlineKeyboardBuilder()
    
    # Генеруємо кнопки для кожної черги з JSON
    for queue_name in schedules.keys():
        builder.add(types.InlineKeyboardButton(text=f"Черга {queue_name}", callback_data=f"set_q_{queue_name}"))
    
    builder.adjust(2) # по 2 кнопки в рядку
    await callback.message.edit_text("Оберіть вашу чергу відключень:", reply_markup=builder.as_markup())
    await callback.answer()

# Збереження обраної черги
@dp.callback_query(F.data.startswith("set_q_"))
async def process_set_queue(callback: types.CallbackQuery):
    queue_name = callback.data.split("_")[2]
    await update_user_queue(callback.from_user.id, queue_name)
    
    await callback.message.edit_text(
        f"✅ Успішно! Вашу чергу змінено на **{queue_name}**.\n\n"
        "Тепер ви можете переглянути актуальний графік.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⚡ Подивитися графік", callback_data="get_schedule")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

# Перегляд графіка для своєї черги
@dp.callback_query(F.data == "get_schedule")
async def process_get_schedule(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_queue = await get_user_queue(user_id)
    schedules = load_schedules()
    
    if current_queue not in schedules:
        await callback.message.answer("⚠️ На жаль, графік для вашої черги поки не знайдено в базі.")
        await callback.answer()
        return
    
    queue_data = schedules[current_queue]
    response_text = f"📅 **Графік відключень для черги {current_queue}:**\n\n"
    
    for day, times in queue_data.items():
        times_str = ", ".join(times) if isinstance(times, list) else times
        response_text.-append(f"• **{day}**: {times_str}\n") if hasattr(response_text, 'append') else None # захист форматування
        
    # Формуємо текст красивіше
    formatted_days = []
    for day, times in queue_data.items():
        t_str = ", ".join(times) if isinstance(times, list) else times
        formatted_days.append(f"🔹 **{day}**: {t_str}")
        
    final_text = f"📅 **Графік відключень для черги {current_queue}:**\n\n" + "\n".join(formatted_days)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⚙️ Змінити чергу", callback_data="change_queue"))
    
    await callback.message.edit_text(final_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

# Головна функція запуску
async def main():
    await init_db()
    logging.info("Бот запущено та готовий до роботи!")
    # Запускаємо веб-сервер у фоні для Render
    keep_alive()
    # Запускаємо опитування Telegram API
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  

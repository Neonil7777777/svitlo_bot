import os
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask
from threading import Thread

from db import init_db, add_user, update_user_address, get_user_address

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не знайдено BOT_TOKEN у змінних середовища!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_schedules():
    try:
        with open("schedules.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Помилка завантаження schedules.json: {e}")
        return {}

# Веб-заглушка для Render
app = Flask('')

@app.route('/')
def home():
    return "Svitlo Bot is running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await add_user(user.id, user.username or user.first_name)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="⚡ Подивитися графік за адресою", callback_data="get_schedule"),
        types.InlineKeyboardButton(text="📍 Змінити адресу", callback_data="change_address")
    )
    
    text = (
        f"Вітаю, {user.first_name}! 🇺🇦\n"
        "Бот для моніторингу світла у Вишневому та регіоні за адресою.\n\n"
        "Оберіть дію:"
    )
    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "change_address")
async def process_change_address(callback: types.CallbackQuery):
    schedules = load_schedules()
    builder = InlineKeyboardBuilder()
    
    for addr in schedules.keys():
        builder.add(types.InlineKeyboardButton(text=addr, callback_data=f"set_addr_{addr}"))
    
    builder.adjust(1)
    await callback.message.edit_text("Оберіть вашу вулицю/адресу зі списку:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_addr_"))
async def process_set_address(callback: types.CallbackQuery):
    address_name = callback.data.replace("set_addr_", "")
    await update_user_address(callback.from_user.id, address_name)
    
    await callback.message.edit_text(
        f"✅ Адресу успішно змінено на: **{address_name}**.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⚡ Подивитися графік", callback_data="get_schedule")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "get_schedule")
async def process_get_schedule(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_address = await get_user_address(user_id)
    schedules = load_schedules()
    
    if current_address not in schedules:
        await callback.message.answer("⚠️ Графік для цієї адреси наразі відсутній.")
        await callback.answer()
        return
    
    queue_data = schedules[current_address]
    formatted_days = []
    for day, times in queue_data.items():
        t_str = ", ".join(times) if isinstance(times, list) else times
        formatted_days.append(f"🔹 **{day}**: {t_str}")
        
    final_text = f"📅 **Графік відключень для адреси ({current_address}):**\n\n" + "\n".join(formatted_days)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📍 Змінити адресу", callback_data="change_address"))
    
    await callback.message.edit_text(final_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

async def main():
    await init_db()
    logging.info("Бот запущено!")
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  

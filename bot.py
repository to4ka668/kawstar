import os
import sys
import asyncio
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from handlers import user_router, admin_router

logging.basicConfig(level=logging.INFO)

async def main():
    if BOT_TOKEN == "PASTE_BOT_TOKEN_HERE" or not BOT_TOKEN:
        raise RuntimeError("Укажите валидный BOT_TOKEN в файле .env или переменных окружения!")

    init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Include Admin router first so admin commands take precedence
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logging.info(f"⭐ KAW Star Bot v0.2 запущен! (ADMIN_ID: {ADMIN_ID})")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")

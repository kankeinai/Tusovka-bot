import asyncio
import logging
import secrets
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Union
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from settings import phrases, info_message, help_message
from random import choice
import json
from settings import settings
from db import db
from repository.user import UserRepository

user_repo = UserRepository()
# Initialize storage
storage = MemoryStorage()

# Initialize dispatcher
dp = Dispatcher(storage=storage)


@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Save user to database
    await user_repo.save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )

    if message.from_user.id in settings.ADMINS and message.from_user.id not in user_repo.get_admins():
        user_repo.set_admin(message.from_user.id)

    welcome_message = (
        f"👋 Hello, {html.bold(message.from_user.full_name)}!\n\n"
        f"Welcome to the Aaltoes Community Bot! \n\n"
        f"Type /help to see all available commands!"
    )

    await message.answer(welcome_message)

@dp.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages"""
    await message.answer("hi!")

async def main() -> None:
    
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Connect to the database
    await db.connect(settings.DATABASE_URL_UNPOOLED)
    # Initialize tables
    await user_repo.init(db)
   
    periodic_tasks = []
    
    # Start periodic tasks and bot polling concurrently
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            *periodic_tasks
        )
    finally:
        # Close the database connection when the bot is stopped
        await db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
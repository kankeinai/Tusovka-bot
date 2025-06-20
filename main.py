import asyncio
import logging
import secrets
import sys
import os
from settings import get_test_time_limit
from datetime import datetime, timedelta
from settings import writing_parts_names
from typing import Dict, List, Tuple, Any, Union
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from random import choice
import json
from settings import settings
from db import db
from repository.user import UserRepository
from repository.invites import InviteRepository
from repository.test import TestRepository
from openai_service import openai_service

user_repo = UserRepository()
invite_repo = InviteRepository()
test_repo = TestRepository()
# Initialize storage
storage = MemoryStorage()

# Initialize dispatcher
dp = Dispatcher(storage=storage)

# State group for invite code creation
class InviteCodeStates(StatesGroup):
    waiting_for_uses = State()

# State group for user registration
class RegistrationStates(StatesGroup):
    waiting_for_invite_code = State()
    waiting_for_name = State()

# State group for test responses
class TestStates(StatesGroup):
    waiting_for_response = State()

# Global bot instance for periodic tasks
bot_instance = None
# Global dispatcher instance for state management
dp_instance = None

# Dictionary to store scheduled tasks
scheduled_tasks = {}

@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Get user from database
    user = await user_repo.get_user(message.from_user.id)

    if user is None:
        # User doesn't exist, create new user
        await user_repo.save_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name
        )
        user = await user_repo.get_user(message.from_user.id)
    else:
        # User exists, update username if changed
        if user['username'] != message.from_user.username:
            await user_repo.update_user(message.from_user.id, username=message.from_user.username)

    if str(message.from_user.id) in settings.ADMINS and not await user_repo.is_admin(message.from_user.id):
        await user_repo.set_admin(message.from_user.id)

    # Save user's language to state
    await state.update_data(language=user['language'])

    welcome_message = (
        f"👋 Привет!{html.bold(message.from_user.full_name)}!\n\n"
        f"Я бот который помогает готовиться к YKI.\n\n"
    )

    await message.answer(welcome_message)

    # Check if user is invited
    if user['invited'] == False:
        await message.answer("Пожалуйста, подтвердите свою учетную запись, чтобы получить доступ к боту! /confirm")

@dp.message(Command("confirm"))
async def command_confirm_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/confirm` command
    """
    user = await user_repo.get_user(message.from_user.id)
    if user['invited'] == True:
        await message.answer("Вы уже подтвердили свою учетную запись!")
    else:

        await message.answer("Введите код приглашения для подтверждения учетной записи")
        await state.set_state(RegistrationStates.waiting_for_invite_code)

@dp.message(RegistrationStates.waiting_for_invite_code)
async def handle_invite_code_input(message: Message, state: FSMContext) -> None:
    """
    Handle invite code input for registration
    """
    if message.text == "/cancel":
        await message.answer("Отмена регистрации.")
        await state.clear()
        return
    
    invite_code = message.text.strip()
    
    # Check if invite code is valid
    valid_invite = await invite_repo.is_valid_invite(invite_code)
    if valid_invite:
        await invite_repo.use_invite(invite_code)
        await user_repo.update_user(
            message.from_user.id,
            invited=True,
            invited_by=valid_invite['created_by']
        )
        await message.answer("Теперь вы можете использовать бота!")
        await state.clear()
    else:
        await message.answer("❌ Неверный код приглашения или код уже использован. Попробуйте еще раз.")

@dp.message(Command("menu"))
async def command_menu_handler(message: Message) -> None:
    """
    This handler receives messages with `/menu` command
    """
    await message.answer("Выберите действие:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Change name", callback_data="change_name")],
        [InlineKeyboardButton(text="Change language", callback_data="change_language")],
    ]))
@dp.callback_query(F.data == "change_language")
async def callback_change_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "change_language" data
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ru", callback_data="language_ru")],
        [InlineKeyboardButton(text="en", callback_data="language_en")],
        [InlineKeyboardButton(text="fi", callback_data="language_fi")],
        [InlineKeyboardButton(text="kz", callback_data="language_kz")],
        [InlineKeyboardButton(text="back", callback_data="back")],
    ])
    await callback.message.edit_text("Выберите язык:", reply_markup=keyboard)

@dp.callback_query(F.data == "back")
async def callback_back_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "back" data
    """
    await callback.message.edit_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Change name", callback_data="change_name")],
        [InlineKeyboardButton(text="Change language", callback_data="change_language")],
    ]))

@dp.callback_query(F.data.startswith("language_"))
async def callback_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "language_" data
    """
    language = callback.data.split("_")[1]
    await user_repo.update_user(callback.from_user.id, language=language)
    
    # Update the language in user's state
    await state.update_data(language=language)
    
    await callback.message.edit_text("Язык успешно изменен на " + language + "!")

@dp.callback_query(F.data == "change_name")
async def callback_change_name_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "change_name" data
    """
    user = await user_repo.get_user(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="back", callback_data="back")],
    ])
    await callback.message.edit_text("Ваше текущее имя: " + user['name'] + "\nВведите новое имя. /cancel для отмены", reply_markup=keyboard)
    await state.set_state(RegistrationStates.waiting_for_name)

@dp.message(RegistrationStates.waiting_for_name)
async def handle_name_input(message: Message, state: FSMContext) -> None:
    """
    Handle the name input for registration
    """
    if message.text == "/cancel":
        await message.answer("Отмена изменения имени.")
        await state.clear()
        return
    
    await user_repo.update_user(message.from_user.id, name=message.text)
    await message.answer("Имя успешно изменено!")
    await state.clear()

@dp.message(Command("code"))
async def command_code_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/invite` command
    """
    await message.answer("Сколько раз можно использовать код? (введите положительное число)")
    await state.set_state(InviteCodeStates.waiting_for_uses)

@dp.message(InviteCodeStates.waiting_for_uses)
async def handle_uses_input(message: Message, state: FSMContext) -> None:
    """
    Handle the number of uses input for invite code
    """
    if message.text == "/cancel":
        await message.answer("Отмена создания кода приглашения.")
        await state.clear()
        return
    try:
        uses = int(message.text)
        if uses <= 0:
            await message.answer("Пожалуйста, введите положительное число больше 0.")
            return
        
        # Generate a shorter, more copy-friendly code (8 characters)
        code = secrets.token_hex(4).upper()
        
        # Create the invite code in database
        success = await invite_repo.create_invite(
            code=code,
            created_by=message.from_user.id,
            max_uses=uses
        )
        
        if success:
            # Send the main message
            await message.answer(
                f"✅ Код приглашения создан!\n\n"
                f"🔄 Лимит использования: {uses} раз\n\n"
            )
            # Send the copyable code as a separate message
            await message.answer(
                f"{code}",
            )
        else:
            await message.answer("❌ Ошибка при создании кода. Попробуйте еще раз.")
        
        await state.clear()
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")

@dp.message(Command("test"))
async def command_test_handler(message: Message) -> None:
    """
    This handler receives messages with `/test` command
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=writing_parts_names[part], callback_data=f"writing_part_{part}") for part in writing_parts_names]
    ])
    await message.answer("Choose a part to write:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("writing_part_"))
async def callback_writing_part_1_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "writing_part_1" data
    """
    test_type = callback.data
    user = await user_repo.get_user(callback.from_user.id)
    
    # Show loading message
    await callback.message.edit_text(f"🔄 Генерирую тему для {writing_parts_names[test_type]}...")
    
    try:
        # Get test topic from OpenAI
        topic = await openai_service.get_test_topic(user['language'], test_type, user['level'])
        
        # Create test record in database
        test_id = await test_repo.create_test(test_type, callback.from_user.id, topic, user['level'])
        
        if test_id:
            # Get time limit for this test type
            # Save test_id to state
            await state.update_data(current_test_id=test_id, warnings_sent=[])
            
            # Set state (MemoryStorage doesn't support expiration directly)
            await state.set_state(TestStates.waiting_for_response)
            
            # Schedule warning and completion tasks
            await schedule_test_tasks(test_id, callback.from_user.id, test_type, bot_instance)
            
            # Send the topic and instructions
            await callback.message.edit_text(
                f"📝 **Epämuodollinen viesti - YKI Testti**\n\n{topic}\n\n",
                parse_mode="Markdown"
            )
            await callback.message.answer(f"You have {get_test_time_limit(test_type)} minutes to write your response.")
        else:
            await callback.message.edit_text(
                "❌ Ошибка при создании теста. Попробуйте позже."
            )
        
    except Exception as e:
        logging.error(f"Error generating test topic: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при генерации темы. Попробуйте позже."
        )

async def schedule_test_tasks(test_id: int, user_id: int, test_type: str, bot: Bot):
    """Schedule warning and completion tasks for a specific test."""
    from settings import get_test_time_limit
    
    time_limit_minutes = get_test_time_limit(test_type)
    
    # Calculate delays in seconds
    warning_5min_delay = (time_limit_minutes - 5) * 60  # 5 minutes before end
    warning_1min_delay = (time_limit_minutes - 1) * 60  # 1 minute before end
    completion_delay = time_limit_minutes * 60           # At the end
    
    # Schedule 5-minute warning
    if warning_5min_delay > 0:
        task_5min = asyncio.create_task(
            send_scheduled_warning(test_id, user_id, 5, warning_5min_delay, bot)
        )
        scheduled_tasks[f"{test_id}_5min"] = task_5min
    
    # Schedule 1-minute warning
    if warning_1min_delay > 0:
        task_1min = asyncio.create_task(
            send_scheduled_warning(test_id, user_id, 1, warning_1min_delay, bot)
        )
        scheduled_tasks[f"{test_id}_1min"] = task_1min
    
    # Schedule test completion
    task_completion = asyncio.create_task(
        auto_complete_test(test_id, user_id, completion_delay, bot)
    )
    scheduled_tasks[f"{test_id}_completion"] = task_completion
    
    logging.info(f"Scheduled tasks for test {test_id}: 5min warning at {warning_5min_delay}s, 1min warning at {warning_1min_delay}s, completion at {completion_delay}s")

async def send_scheduled_warning(test_id: int, user_id: int, minutes_left: int, delay: float, bot: Bot):
    """Send a scheduled warning message after the specified delay."""
    try:
        await asyncio.sleep(delay)
        
        # Check if test is still active
        test = await test_repo.get_test(test_id)
        if not test or test['finished']:
            logging.info(f"Test {test_id} already finished, skipping {minutes_left}-min warning")
            return
        
        warning_messages = {
            5: "⚠️ Внимание! До окончания теста осталось 5 минут!",
            1: "🚨 Срочно! До окончания теста осталось 1 минута!"
        }
        
        message = warning_messages.get(minutes_left, f"⏰ До окончания теста осталось {minutes_left} минут!")
        
        await bot.send_message(user_id, message)
        logging.info(f"Sent scheduled {minutes_left}-minute warning to user {user_id} for test {test_id}")
        
    except Exception as e:
        logging.error(f"Failed to send scheduled warning: {e}")

async def clear_user_state_via_dispatcher(user_id: int, bot: Bot):
    """Clear user's state using dispatcher's FSM context."""
    try:
        if dp_instance:
            state = dp_instance.fsm.get_context(
                bot=bot,
                chat_id=user_id,
                user_id=user_id,
            )
            await state.clear()
            logging.info(f"Cleared state for user {user_id} via dispatcher")
        else:
            logging.warning(f"Could not clear state for user {user_id} - dispatcher not available")
    except Exception as e:
        logging.error(f"Failed to clear user state via dispatcher: {e}")

async def auto_complete_test(test_id: int, user_id: int, delay: float, bot: Bot):
    """Automatically complete a test after the specified delay."""
    try:
        await asyncio.sleep(delay)
        
        # Check if test is still active
        test = await test_repo.get_test(test_id)
        if not test or test['finished']:
            logging.info(f"Test {test_id} already finished, skipping auto-completion")
            return
        
        # Get the last response from the database
        last_response = test.get('response')

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="What is my score?", callback_data=f"grade_{test_id}")],
            [InlineKeyboardButton(text="How can I improve?", callback_data=f"feedback_{test_id}")],
            [InlineKeyboardButton(text="What do I need to practice?", callback_data=f"advice_{test_id}")],
        ])
        
        if last_response:
            # User provided a response, finish the test with it
            await test_repo.db.execute("""
                UPDATE tests 
                SET finished = TRUE, 
                    finished_at = NOW()
                WHERE id = $1
            """, test_id)
            
            await bot.send_message(
                user_id, 
                f"⏰ Время теста истекло!", 
                reply_markup=keyboard
            )
        else:
            # No response provided, mark as auto-finished
            await test_repo.db.execute("""
                UPDATE tests 
                SET finished = TRUE, 
                    finished_at = NOW(),
                    response = 'AUTO_FINISHED: Time limit exceeded'
                WHERE id = $1
            """, test_id)
            
            # Send completion message
            await bot.send_message(user_id, "⏰ Время теста истекло! Ответ не был предоставлен.")
        
        # Clear user's state using dispatcher
        await clear_user_state_via_dispatcher(user_id, bot)
        
        logging.info(f"Auto-completed test {test_id} for user {user_id}")
        
    except Exception as e:
        logging.error(f"Failed to auto-complete test: {e}")

def cancel_scheduled_tasks(test_id: int):
    """Cancel all scheduled tasks for a specific test."""
    task_keys = [f"{test_id}_5min", f"{test_id}_1min", f"{test_id}_completion"]
    
    for key in task_keys:
        if key in scheduled_tasks:
            task = scheduled_tasks[key]
            if not task.done():
                task.cancel()
            del scheduled_tasks[key]
    
    logging.info(f"Cancelled scheduled tasks for test {test_id}")

@dp.callback_query(F.data.startswith("grade_"))
async def callback_grade_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "grade_" data
    """
    try:
        test_id = int(callback.data.split("_")[1])
        logging.info(f"Grade test {test_id} for user {callback.from_user.id}")
        test = await test_repo.get_test(test_id)
        
        if not test:
            await callback.message.edit_text("❌ Тест не найден.")
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        prompt = f"Provide response in {user['language']} language. Grade this response against criteria on {test['test_level']} level yki, this writing task is {writing_parts_names[test['test_type']]}, topic was \"{test['topic']}\", provide numerical grade according to YKI grading scale: {test['response']}."
        await callback.message.answer("🔄 Генерирую оценку...")
        grade = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(f"📊 Оценка: {grade}")
    except Exception as e:
        logging.error(f"Error in grade handler: {e}")
        await callback.message.edit_text("❌ Ошибка при генерации оценки. Попробуйте позже.")

@dp.callback_query(F.data.startswith("feedback_"))
async def callback_feedback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "feedback_" data
    """
    try:
        test_id = int(callback.data.split("_")[1])
        test = await test_repo.get_test(test_id)
        
        if not test:
            await callback.message.edit_text("❌ Тест не найден.")
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        prompt = f"How can I improve? Analyze this response and provide specific improvement suggestions for {test['test_level']} level yki, {test['test_type']}, topic was \"{test['topic']}\": {test['response']}. Provide response in {user['language']} language."
        
        await callback.message.answer("🔄 Генерирую рекомендации...")

        feedback = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(f"💡 Рекомендации: {feedback}")
    except Exception as e:
        logging.error(f"Error in feedback handler: {e}")
        await callback.message.edit_text("❌ Ошибка при генерации рекомендаций. Попробуйте позже.")

@dp.callback_query(F.data.startswith("advice_"))
async def callback_advice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "advice_" data
    """
    try:
        test_id = int(callback.data.split("_")[1])
        test = await test_repo.get_test(test_id)
        
        if not test:
            await callback.message.edit_text("❌ Тест не найден.")
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        logging.info(f"test {test}")
        prompt = f"What do I need to practice? Based on this response, what specific areas should I focus on for {test['test_level']} level yki, {test['test_type']}, topic was \"{test['topic']}\": {test['response']}. Provide response in {user['language']} language."

        await callback.message.answer("🔄 Генерирую советы...")
        advice = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(f"🎯 Что практиковать: {advice}")

    except Exception as e:
        logging.error(f"Error in advice handler: {e}")
        await callback.message.edit_text("❌ Ошибка при генерации советов. Попробуйте позже.")

@dp.message(TestStates.waiting_for_response)
async def handle_test_response(message: Message, state: FSMContext) -> None:
    """
    Handle user's test response - allows multiple responses
    """
    if message.text == "/cancel":
        # Cancel the test and scheduled tasks
        data = await state.get_data()
        test_id = data.get('current_test_id')
        
        if test_id:
            await test_repo.cancel_active_test(message.from_user.id)
            cancel_scheduled_tasks(test_id)
        
        await message.answer("❌ Тест отменен.")
        await state.clear()
        return
    
    # Get test data from state
    data = await state.get_data()
    test_id = data.get('current_test_id')
    
    if not test_id:
        await message.answer("❌ Ошибка: тест не найден. Начните заново.")
        await state.clear()
        return

    
    # Store the latest response in state and database
    await state.update_data(last_response=message.text)
    await test_repo.update_last_response(test_id, message.text)
    
    # Show confirmation but don't finish the test yet
    await message.answer(
        "✅ Ответ сохранен! Вы можете отправить новый ответ или дождаться окончания времени."
    )

@dp.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages"""
    await message.answer("hi!")

async def main() -> None:
    global bot_instance, dp_instance
    
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot_instance = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Connect to the database
    await db.connect(settings.DATABASE_URL_UNPOOLED)
    # Initialize tables
    await user_repo.init(db)
    await invite_repo.init(db)
    await test_repo.init(db)

    # Set global dispatcher instance
    dp_instance = dp

    await dp.start_polling(bot_instance)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
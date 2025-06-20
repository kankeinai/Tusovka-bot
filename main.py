import asyncio
import logging
from settings import get_test_time_limit, get_text, writing_parts_names
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Union
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from settings import settings
from db import db
from repository.user import UserRepository
from repository.invites import InviteRepository
from repository.test import TestRepository
from openai_service import openai_service
import aiohttp
from aiohttp import web

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
    user = await user_repo.get_user(message.from_user.id)
    
    if user and user['invited']:
        # User is already registered and confirmed
        await message.answer(get_text('welcome', user['language']))
    elif user and not user['invited']:
        # User is registered but not confirmed
        await message.answer(get_text('confirm_registration', user['language']))
        await state.set_state(RegistrationStates.waiting_for_name)
    else:
        # New user, start registration
        await message.answer(get_text('invite_code_prompt', 'ru'))
        await state.set_state(RegistrationStates.waiting_for_invite_code)

@dp.message(Command("confirm"))
async def command_confirm_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/confirm` command
    """
    user = await user_repo.get_user(message.from_user.id)
    
    if user and not user['invited']:
        await user_repo.update_user(message.from_user.id, confirmed=True)
        await message.answer(get_text('registration_success', user['language']))
        await command_menu_handler(message)
    else:
        await message.answer(get_text('not_registered', user['language'] if user else 'ru'))

@dp.message(RegistrationStates.waiting_for_invite_code)
async def handle_invite_code_input(message: Message, state: FSMContext) -> None:
    """
    Handle invite code input during registration
    """
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
        await message.answer(get_text('registration_success', 'ru'))
        await state.clear()
    else:
        await message.answer(get_text('invalid_invite', 'ru'))

@dp.message(Command("menu"))
async def command_menu_handler(message: Message) -> None:
    """
    This handler receives messages with `/menu` command
    """
    user = await user_repo.get_user(message.from_user.id)
    
    if not user or not user['invited']:
        await message.answer(get_text('not_registered', user['language'] if user else 'ru'))
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text('change_name', user['language']), callback_data="change_name")],
        [InlineKeyboardButton(text=get_text('change_language', user['language']), callback_data="change_language")],
        [InlineKeyboardButton(text=get_text('change_level', user['language']), callback_data="change_level")],
    ])
    
    await message.answer(get_text('menu_title', user['language']), reply_markup=keyboard)

@dp.callback_query(F.data == "change_language")
async def callback_change_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "change_language" data
    """
    user = await user_repo.get_user(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="language_ru")],
        [InlineKeyboardButton(text="English", callback_data="language_en")],
        [InlineKeyboardButton(text="Suomi", callback_data="language_fi")],
        [InlineKeyboardButton(text="Қазақ", callback_data="language_kz")],
        [InlineKeyboardButton(text=get_text('back', user['language']), callback_data="back")],
    ])
    await callback.message.edit_text(get_text('choose_language', user['language']), reply_markup=keyboard)

@dp.callback_query(F.data == "change_level")
async def callback_change_level_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "change_level" data
    """
    user = await user_repo.get_user(callback.from_user.id)
    await callback.message.edit_text(get_text('choose_level', user['language']), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Basic", callback_data="level_basic")],
        [InlineKeyboardButton(text="Intermediate", callback_data="level_intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="level_advanced")],
        [InlineKeyboardButton(text=get_text('back', user['language']), callback_data="back")],
    ]))

@dp.callback_query(F.data.startswith("level_"))
async def callback_level_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "level_" data
    """
    level = callback.data.split("_")[1]
    user = await user_repo.get_user(callback.from_user.id)
    await user_repo.update_user(callback.from_user.id, level=level)
    await callback.message.edit_text(get_text('level_changed', user['language'], level=level))

@dp.callback_query(F.data == "back")
async def callback_back_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "back" data
    """
    await command_menu_handler(callback.message)

@dp.callback_query(F.data.startswith("language_"))
async def callback_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "language_" data
    """
    language = callback.data.split("_")[1]
    await user_repo.update_user(callback.from_user.id, language=language)
    
    # Update the language in user's state
    await state.update_data(language=language)
    
    await callback.message.edit_text(get_text('language_updated', language))

@dp.callback_query(F.data == "change_name")
async def callback_change_name_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "change_name" data
    """
    user = await user_repo.get_user(callback.from_user.id)
    await callback.message.edit_text(get_text('name_prompt', user['language']))
    await state.set_state(RegistrationStates.waiting_for_name)

@dp.message(RegistrationStates.waiting_for_name)
async def handle_name_input(message: Message, state: FSMContext) -> None:
    """
    Handle name input during registration or name change
    """
    user = await user_repo.get_user(message.from_user.id)
    name = message.text.strip()
    
    if user and user['invited']:
        # Changing name for existing user
        await user_repo.update_user(message.from_user.id, name=name)
        await message.answer(get_text('name_updated', user['language']))
        await state.clear()
    else:
        # New user registration
        await user_repo.update_user(message.from_user.id, name=name)
        await message.answer(get_text('confirm_registration', 'ru'))
        await state.clear()

@dp.message(Command("code"))
async def command_code_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/code` command
    """
    await message.answer("Enter number of uses for the invite code:")
    await state.set_state(InviteCodeStates.waiting_for_uses)

@dp.message(InviteCodeStates.waiting_for_uses)
async def handle_uses_input(message: Message, state: FSMContext) -> None:
    """
    Handle uses input for invite code creation
    """
    try:
        uses = int(message.text.strip())
        invite_code = await invite_repo.create_invite(message.from_user.id, uses)
        await message.answer(f"Invite code created: {invite_code}")
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid number.")

@dp.message(Command("test"))
async def command_test_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/test` command
    """
    user = await user_repo.get_user(message.from_user.id)
    
    if not user or not user['invited']:
        await message.answer(get_text('not_registered', user['language'] if user else 'ru'))
        return
    
    if await state.get_state() == TestStates.waiting_for_response:
        await message.answer(get_text('already_in_test', user['language']))
        return
    
    keyboard_buttons = []
    for part in writing_parts_names:
        keyboard_buttons.append([InlineKeyboardButton(text=writing_parts_names[part], callback_data=part)])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(get_text('choose_part', user['language']), reply_markup=keyboard)

@dp.callback_query(F.data.startswith("writing_part_"))
async def callback_writing_part_1_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "writing_part_1" data
    """
    test_type = callback.data
    logging.info(f"test_type: {test_type}")
    user = await user_repo.get_user(callback.from_user.id)
    
    # Show loading message
    await callback.message.edit_text(get_text('generating_topic', user['language'], topic=writing_parts_names[test_type]))
    
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
                get_text('test_title', user['language'], title=writing_parts_names[test_type], topic=topic),
                parse_mode="Markdown"
            )
            await callback.message.answer(get_text('test_time_limit', user['language'], minutes=get_test_time_limit(test_type)))
        else:
            await callback.message.edit_text(get_text('test_creation_error', user['language']))
        
    except Exception as e:
        logging.error(f"Error generating test topic: {e}")
        await callback.message.edit_text(get_text('test_creation_error', user['language']))

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
    """Send a scheduled warning message to the user."""
    try:
        await asyncio.sleep(delay)
        
        # Check if test is still active
        test = await test_repo.get_test(test_id)
        if not test or test['finished']:
            logging.info(f"Test {test_id} already finished, skipping {minutes_left}-minute warning")
            return
        
        user = await user_repo.get_user(user_id)
        
        warning_messages = {
            5: get_text('warning_5min', user['language']),
            1: get_text('warning_1min', user['language'])
        }
        
        message = warning_messages.get(minutes_left, get_text('warning_generic', user['language'], minutes=minutes_left))
        
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
        
        user = await user_repo.get_user(user_id)
        
        # Get the last response from the database
        last_response = test.get('response')

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text('what_is_my_score', user['language']), callback_data=f"grade_{test_id}")],
            [InlineKeyboardButton(text=get_text('how_can_i_improve', user['language']), callback_data=f"feedback_{test_id}")],
            [InlineKeyboardButton(text=get_text('what_do_i_need_to_practice', user['language']), callback_data=f"advice_{test_id}")],
        ])
        
        if last_response:
            prompt = (
                f"I have this text: \"{test['response']}\". "
                f"The writing task is: {writing_parts_names[test['test_type']]}. "
                f"The topic is: \"{test['topic']}\". "
                "Give only a single numerical grade (0–6) according to the official YKI grading scale. "
                "Do not explain, comment, or add any extra text. Be strict and follow all YKI criteria. "
                "If the text is off-topic, give a score of 0."
            )

            get_numerical_grade = await openai_service.get_numeric_grade(user['language'], prompt, test['test_level'], test['topic'])
            # User provided a response, finish the test with it
            await test_repo.db.execute("""
                UPDATE tests 
                SET finished = TRUE, 
                    finished_at = NOW(),
                    grade = $2
                WHERE id = $1
            """, test_id, get_numerical_grade)
            
            await bot.send_message(
                user_id, 
                get_text('time_expired', user['language']), 
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
            await bot.send_message(user_id, get_text('no_response_provided', user['language']))
        
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
            user = await user_repo.get_user(callback.from_user.id)
            await callback.message.edit_text(get_text('test_not_found_error', user['language']))
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        prompt = (
            f"Evaluate this response for the YKI writing exam:\n"
            f"Text: \"{test['response']}\"\n"
            f"Level: {test['test_level']}, Task: {writing_parts_names[test['test_type']]}, Topic: \"{test['topic']}\".\n"
            "Give a numerical grade (0–6) and explain the score based on YKI criteria: content, structure, vocabulary, grammar, and task completion. "
            f"Justify each part with specific examples from the text. Be strict and accurate. Respond in {user['language']}."
            "Limit your response to 200 words."        
        )

        # Use the new numeric grade method
        grade = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(get_text('grade_title', user['language'], grade=grade), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in grade handler: {e}")
        user = await user_repo.get_user(callback.from_user.id)
        await callback.message.edit_text(get_text('grade_error', user['language']))

@dp.callback_query(F.data.startswith("feedback_"))
async def callback_feedback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "feedback_" data
    """
    try:
        test_id = int(callback.data.split("_")[1])
        test = await test_repo.get_test(test_id)
        
        if not test:
            user = await user_repo.get_user(callback.from_user.id)
            await callback.message.edit_text(get_text('test_not_found_error', user['language']))
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        logging.info(f"test: {test['response']}")
        prompt = (
            f"Analyze the following YKI writing response:\n"
            f"Text: \"{test['response']}\"\n"
            f"Level: {test['test_level']}, Task: {writing_parts_names[test['test_type']]}, Topic: \"{test['topic']}\".\n"
            "Comment on grammar, vocabulary, sentence structure, and content relevance. "
            "Point out strong parts and give examples of errors or weak areas. "
            f"Be detailed and refer to specific parts of the text. Respond in {user['language']}."
            "Limit your response to 200 words."
        )
 
        await callback.message.answer(get_text('generating_feedback', user['language']))

        feedback = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(get_text('feedback_title', user['language'], feedback=feedback), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in feedback handler: {e}")
        user = await user_repo.get_user(callback.from_user.id)
        await callback.message.edit_text(get_text('feedback_error', user['language']))

@dp.callback_query(F.data.startswith("advice_"))
async def callback_advice_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    This handler receives callback queries with "advice_" data
    """
    try:
        test_id = int(callback.data.split("_")[1])
        test = await test_repo.get_test(test_id)
        
        if not test:
            user = await user_repo.get_user(callback.from_user.id)
            await callback.message.edit_text(get_text('test_not_found_error', user['language']))
            return
            
        user = await user_repo.get_user(callback.from_user.id)
        logging.info(f"test {test}")
        prompt = (
            f"Based on this YKI writing response:\n"
            f"Text: \"{test['response']}\"\n"
            f"Level: {test['test_level']}, Task: {writing_parts_names[test['test_type']]}, Topic: \"{test['topic']}\".\n"
            "What should the student focus on to improve their score? "
            "Suggest specific grammar rules, vocabulary areas, or writing skills to train. "
            f"Mention concrete exercises or resources. Use examples from the text to guide your suggestions. Respond in {user['language']}."
            "Limit your response to 200 words."
        )
        await callback.message.answer(get_text('generating_advice', user['language']))
        advice = await openai_service.get_response(user['language'], prompt, test['test_level'], test['topic'])

        await callback.message.answer(get_text('advice_title', user['language'], advice=advice), parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error in advice handler: {e}")
        user = await user_repo.get_user(callback.from_user.id)
        await callback.message.edit_text(get_text('advice_error', user['language']))

@dp.message(TestStates.waiting_for_response)
async def handle_test_response(message: Message, state: FSMContext) -> None:
    """
    Handle user's test response - allows multiple responses
    """
    user = await user_repo.get_user(message.from_user.id)
    
    if message.text == "/cancel":
        # Cancel the test and scheduled tasks
        data = await state.get_data()
        test_id = data.get('current_test_id')
        
        if test_id:
            await test_repo.cancel_active_test(message.from_user.id)
            cancel_scheduled_tasks(test_id)
        
        await message.answer(get_text('test_cancelled', user['language']))
        await state.clear()
        return
    
    # Get test data from state
    data = await state.get_data()
    test_id = data.get('current_test_id')
    
    if not test_id:
        await message.answer(get_text('test_not_found', user['language']))
        await state.clear()
        return

    
    # Store the latest response in state and database
    await state.update_data(last_response=message.text)
    await test_repo.update_last_response(test_id, message.text)
    
    # Show confirmation but don't finish the test yet
    await message.answer(get_text('response_saved', user['language']))

@dp.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages"""
    user = await user_repo.get_user(message.from_user.id)
    await message.answer(get_text('unknown_message', user['language'] if user else 'ru'))

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

    # Create web app for health checks
    app = web.Application()
    
    # Health check endpoint
    async def health_check(request):
        return web.Response(text="OK", status=200)
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Root endpoint also returns health status
    
    # Create runner for web app
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Start web server on port 8080
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("Health check server started on port 8080")
    
    try:
        # Start both the bot and keep the web server running
        await dp.start_polling(bot_instance)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
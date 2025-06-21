from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import os
from dataclasses import dataclass
from typing import Dict, Any

# Load environment variables first
load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL_UNPOOLED: str = os.getenv("DATABASE_URL_UNPOOLED", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ADMINS: list[str] = [
        '658415666',
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"  # This will ignore extra environment variables

# Initialize settings
settings = Settings()

languages = {
    'ru': 'russian',
    'en': 'english',
    'fi': 'finnish',
    'kz': 'kazakh'
}

system_message = """
You are a strict but supportive assistant for Tusovka language school, helping students prepare for the YKI Finnish exam. You always provide clear, concise, and constructive feedback in the student's preferred language. Your evaluations follow YKI criteria closely and highlight exactly what needs to be improved. Be firm, fair, and focused on progress.
YKI score 0 means the response is off-topic, empty, or completely fails to show any usable language skills.
YKI score 1 means the response shows very limited language ability with major errors and unclear communication.
YKI score 2 means the response shows some basic language skills but with frequent errors and limited ability to express clear ideas.s
YKI score 3 means the response is understandable and mostly on-topic, but contains noticeable errors and limited vocabulary.
YKI score 4 means the response is clear and mostly correct, with occasional mistakes but sufficient language skills for everyday situations
YKI score 5 means the response is fluent, well-structured, and mostly accurate, with only minor errors that do not affect understanding.
YKI score 6 means the response is very fluent, precise, and nearly error-free, demonstrating excellent control of language and style.
"""


tests = {
    'writing_part_1': """
        Generate me topic for writing part 1 test of Finnish YKI (Epämuodollinen viesti — Неформальное сообщение). 
        Provide all instructions that are usually present on the test. Do not include any other text.
        Topic should be in Finnish. 
        Example: write a message to a friend, neighbor, colleague.
        Typical topics: invite, tell about an event, explain a situation.
        Volume: 50–100 words.
    """,
    'writing_part_2': """
        Generate me topic for writing part 2 test of Finnish YKI (Muodollinen viesti — Формальное письмо). 
        Provide all instructions that are usually present on the test.
        Topic should be in Finnish.
        Example: complaint, request, message to an official institution (hospital, school, store).
        Typical topics: cancel a meeting, complaint about a service, request information.
        Volume: 100–150 words.
    """,
    'writing_part_3': """
        Generate me topic for writing part 3 test of Finnish YKI (Mielipideteksti — Выражение мнения). 
        Provide all instructions that are usually present on the test.
        Topic should be in Finnish.
        example: You need to express and justify your opinion on the proposed topic.
        Example topic: "Is it important to practice sports?"
        Volume: 150–200 words.
    """
}

writing_parts_names ={
    'writing_part_1': "Epämuodollinen viesti",
    'writing_part_2': "Muodollinen viesti",
    'writing_part_3': "Mielipideteksti",
}

# Test time limits in minutes
test_time_limits = {
    'writing_part_1': 15,  
    'writing_part_2': 20,  
    'writing_part_3': 25,     
}

def get_test_time_limit(test_type: str) -> int:
    """Get time limit in minutes for a specific test type."""
    return test_time_limits.get(test_type, 30)  # Default 30 minutes

# Language translations
TRANSLATIONS = {
    'ru': {
        'welcome': '👋 Привет! Добро пожаловать в бот для подготовки к YKI!\n\n📝 Используйте /test для начала подготовки\n⚙️ Используйте /menu для настроек',
        'not_registered': '❌ Вы не зарегистрированы\n\nИспользуйте /start для регистрации',
        'menu_title': '⚙️ Настройки',
        'change_name': '✏️ Изменить имя',
        'change_language': '🌍 Изменить язык',
        'change_level': '📊 Изменить уровень',
        'back': '⬅️ Назад',
        'choose_language': '🌍 Выберите язык:',
        'choose_level': '📊 Выберите уровень:',
        'level_changed': '✅ Уровень изменен на {level}!',
        'already_in_test': '⚠️ Вы уже в тесте\n\nЗавершите текущий тест сначала',
        'choose_part': '📝 Выберите часть для написания:',
        'generating_topic': '🔄 Генерирую тему для {topic}...',
        'test_time_limit': '⏰ У вас {minutes} минут на ответ',
        'test_title': '📝 **{title} - YKI Test**\n\n{topic}',
        'test_creation_error': '❌ Ошибка создания теста\n\nПопробуйте позже',
        'response_saved': '✅ Ответ сохранен!\n\nМожете отправить новый ответ или дождаться окончания времени',
        'test_not_found': '❌ Тест не найден\n\nНачните заново',
        'test_cancelled': '❌ Тест отменен',
        'generating_grade': '🔄 Генерирую оценку...',
        'grade_title': '📊 Оценка: {grade}',
        'grade_reason_not_finnish': 'Текст не на финском языке',
        'grade_reason_off_topic': 'Текст не соответствует теме',
        'grade_reason_rejected': 'Текст отклонен',
        'grade_reason_grade_extraction_failed': 'Не удалось извлечь оценку',
        'grade_reason_error_occurred': 'Произошла ошибка при оценке',
        'grade_zero_message': 'Вы получили оценку 0. Причина: {reason}',
        'generating_feedback': '🔄 Генерирую рекомендации...',
        'feedback_title': '💡 **Рекомендации:**\n\n{feedback}',
        'generating_advice': '🔄 Генерирую советы...',
        'advice_title': '🎯 **Что практиковать:**\n\n{advice}',
        'grade_error': '❌ Ошибка генерации оценки\n\nПопробуйте позже',
        'feedback_error': '❌ Ошибка генерации рекомендаций\n\nПопробуйте позже',
        'advice_error': '❌ Ошибка генерации советов\n\nПопробуйте позже',
        'test_not_found_error': '❌ Тест не найден',
        'time_expired': '⏰ Время истекло!',
        'no_response_provided': '⏰ Время истекло!\n\nОтвет не был предоставлен',
        'what_is_my_score': '📊 Какая моя оценка?',
        'how_can_i_improve': '💡 Как улучшиться?',
        'what_do_i_need_to_practice': '🎯 Что практиковать?',
        'confirm_registration': '✅ Подтвердите регистрацию',
        'invite_code_prompt': '🔑 Введите код приглашения:',
        'invalid_invite': '❌ Неверный код приглашения\n\nПопробуйте еще раз',
        'registration_success': '✅ Регистрация успешна!\n\nТеперь можете использовать бота',
        'name_prompt': '✏️ Введите ваше имя:',
        'name_updated': '✅ Имя обновлено!',
        'language_updated': '✅ Язык изменен!',
        'unknown_message': '👋 Привет!',
        'warning_5min': '⚠️ **Внимание!**\n\nДо окончания теста осталось 5 минут!',
        'warning_1min': '🚨 **Срочно!**\n\nДо окончания теста осталось 1 минута!',
        'warning_generic': '⏰ До окончания теста осталось {minutes} минут!',
        'grade_title' : '📊 **Grade:**\n\n{grade}',
    },
    'en': {
        'welcome': '👋 Hi! Welcome to the YKI preparation bot!\n\n📝 Use /test to start preparing\n⚙️ Use /menu for settings',
        'not_registered': '❌ You are not registered\n\nUse /start to register',
        'menu_title': '⚙️ Settings',
        'change_name': '✏️ Change name',
        'change_language': '🌍 Change language',
        'change_level': '📊 Change level',
        'back': '⬅️ Back',
        'choose_language': '🌍 Choose language:',
        'choose_level': '📊 Choose level:',
        'level_changed': '✅ Level changed to {level}!',
        'already_in_test': '⚠️ You are already in a test\n\nPlease finish the current test first',
        'choose_part': '📝 Choose a part to write:',
        'generating_topic': '🔄 Generating topic for {topic}...',
        'test_time_limit': '⏰ You have {minutes} minutes to respond',
        'test_title': '📝 **{title} - YKI Test**\n\n{topic}',
        'test_creation_error': '❌ Error creating test\n\nTry again later',
        'response_saved': '✅ Response saved!\n\nYou can send a new response or wait for time to expire',
        'test_not_found': '❌ Test not found\n\nStart over',
        'test_cancelled': '❌ Test cancelled',
        'generating_grade': '🔄 Generating grade...',
        'grade_title': '📊 Grade: {grade}',
        'grade_reason_not_finnish': 'Text is not in Finnish',
        'grade_reason_off_topic': 'Text is off-topic',
        'grade_reason_rejected': 'Text was rejected',
        'grade_reason_grade_extraction_failed': 'Could not extract grade',
        'grade_reason_error_occurred': 'An error occurred during grading',
        'grade_zero_message': 'You received a score of 0. Reason: {reason}',
        'generating_feedback': '🔄 Generating feedback...',
        'feedback_title': '💡 **Feedback:**\n\n{feedback}',
        'generating_advice': '🔄 Generating advice...',
        'advice_title': '🎯 **What to practice:**\n\n{advice}',
        'grade_error': '❌ Error generating grade\n\nTry again later',
        'feedback_error': '❌ Error generating feedback\n\nTry again later',
        'advice_error': '❌ Error generating advice\n\nTry again later',
        'test_not_found_error': '❌ Test not found',
        'time_expired': '⏰ Time expired!',
        'no_response_provided': '⏰ Time expired!\n\nNo response was provided',
        'what_is_my_score': '📊 What is my score?',
        'how_can_i_improve': '💡 How can I improve?',
        'what_do_i_need_to_practice': '🎯 What do I need to practice?',
        'confirm_registration': '✅ Confirm registration',
        'invite_code_prompt': '🔑 Enter invite code:',
        'invalid_invite': '❌ Invalid invite code\n\nTry again',
        'registration_success': '✅ Registration successful!\n\nYou can now use the bot',
        'name_prompt': '✏️ Enter your name:',
        'name_updated': '✅ Name updated!',
        'language_updated': '✅ Language changed!',
        'unknown_message': '👋 Hi!',
        'warning_5min': '⚠️ **Warning!**\n\n5 minutes left until test ends!',
        'warning_1min': '🚨 **Urgent!**\n\n1 minute left until test ends!',
        'warning_generic': '⏰ {minutes} minutes left until test ends!',
        'grade_title' : '📊 **Grade:**\n\n{grade}',
    },
    'fi': {
        'welcome': '👋 Hei! Tervetuloa YKI-valmennusbottiin!\n\n📝 Käytä /test aloittaaksesi valmennuksen\n⚙️ Käytä /menu asetusten muuttamiseen',
        'not_registered': '❌ Et ole rekisteröitynyt\n\nKäytä /start rekisteröitymiseen',
        'menu_title': '⚙️ Asetukset',
        'change_name': '✏️ Muuta nimeä',
        'change_language': '🌍 Muuta kieltä',
        'change_level': '📊 Muuta tasoa',
        'back': '⬅️ Takaisin',
        'choose_language': '🌍 Valitse kieli:',
        'choose_level': '📊 Valitse taso:',
        'level_changed': '✅ Taso muutettu {level}!',
        'already_in_test': '⚠️ Olet jo testissä\n\nLopeta nykyinen testi ensin',
        'choose_part': '📝 Valitse kirjoitettava osa:',
        'generating_topic': '🔄 Generoin aihetta {topic}...',
        'test_time_limit': '⏰ Sinulla on {minutes} minuuttia vastata',
        'test_title': '📝 **{title} - YKI Testi**\n\n{topic}',
        'test_creation_error': '❌ Virhe testin luomisessa\n\nYritä myöhemmin',
        'response_saved': '✅ Vastaus tallennettu!\n\nVoit lähettää uuden vastauksen tai odottaa ajan umpeutumista',
        'test_not_found': '❌ Testiä ei löytynyt\n\nAloita uudelleen',
        'test_cancelled': '❌ Testi peruttu',
        'generating_grade': '🔄 Generoin arvosanaa...',
        'grade_title': '📊 Arvosana: {grade}',
        'grade_reason_not_finnish': 'Teksti ei ole suomeksi',
        'grade_reason_off_topic': 'Teksti ei liity aiheeseen',
        'grade_reason_rejected': 'Teksti hylättiin',
        'grade_reason_grade_extraction_failed': 'Arvosanaa ei voitu poimia',
        'grade_reason_error_occurred': 'Arvioinnissa tapahtui virhe',
        'grade_zero_message': 'Sait arvosanan 0. Syy: {reason}',
        'generating_feedback': '🔄 Generoin palautetta...',
        'feedback_title': '💡 **Palautetta:**\n\n{feedback}',
        'generating_advice': '🔄 Generoin neuvoja...',
        'advice_title': '🎯 **Mitä harjoitella:**\n\n{advice}',
        'grade_error': '❌ Virhe arvosanan generoinnissa\n\nYritä myöhemmin',
        'feedback_error': '❌ Virhe palautteen generoinnissa\n\nYritä myöhemmin',
        'advice_error': '❌ Virhe neuvojen generoinnissa\n\nYritä myöhemmin',
        'test_not_found_error': '❌ Testiä ei löytynyt',
        'time_expired': '⏰ Aika umpeutui!',
        'no_response_provided': '⏰ Aika umpeutui!\n\nVastausta ei annettu',
        'what_is_my_score': '📊 Mikä on arvosanani?',
        'how_can_i_improve': '💡 Miten voin parantaa?',
        'what_do_i_need_to_practice': '🎯 Mitä minun pitää harjoitella?',
        'confirm_registration': '✅ Vahvista rekisteröityminen',
        'invite_code_prompt': '🔑 Syötä kutsumiskoodi:',
        'invalid_invite': '❌ Virheellinen kutsumiskoodi\n\nYritä uudelleen',
        'registration_success': '✅ Rekisteröityminen onnistui!\n\nNyt voit käyttää bottia',
        'name_prompt': '✏️ Syötä nimesi:',
        'name_updated': '✅ Nimi päivitetty!',
        'language_updated': '✅ Kieli muutettu!',
        'unknown_message': '👋 Hei!',
        'warning_5min': '⚠️ **Varoitus!**\n\n5 minuuttia jäljellä testin loppuun!',
        'warning_1min': '🚨 **Kiireellinen!**\n\n1 minuutti jäljellä testin loppuun!',
        'warning_generic': '⏰ {minutes} minuuttia jäljellä testin loppuun!',
        'grade_title' : '📊 **Grade:**\n\n{grade}',
    },
    'kz': {
        'welcome': '👋 Сәлем! YKI дайындық ботына қош келдіңіз!\n\n📝 /test арқылы дайындықты бастаңыз\n⚙️ /menu арқылы параметрлерді өзгертіңіз',
        'not_registered': '❌ Сіз тіркелмегенсіз\n\nТіркелу үшін /start пайдаланыңыз',
        'menu_title': '⚙️ Параметрлер',
        'change_name': '✏️ Атын өзгерту',
        'change_language': '🌍 Тілді өзгерту',
        'change_level': '📊 Деңгейді өзгерту',
        'back': '⬅️ Артқа',
        'choose_language': '🌍 Тілді таңдаңыз:',
        'choose_level': '📊 Деңгейді таңдаңыз:',
        'level_changed': '✅ Деңгей {level} болып өзгертілді!',
        'already_in_test': '⚠️ Сіз қазірдің өзінде сынақтасыз\n\nАлдымен ағымдағы сынақты аяқтаңыз',
        'choose_part': '📝 Жазу үшін бөлімді таңдаңыз:',
        'generating_topic': '🔄 {topic} тақырыбын жасауда...',
        'test_time_limit': '⏰ Жауап беруге {minutes} минут уақытыңыз бар',
        'test_title': '📝 **{title} - YKI Сынағы**\n\n{topic}',
        'test_creation_error': '❌ Сынақ жасау кезінде қате\n\nКейінірек қайталап көріңіз',
        'response_saved': '✅ Жауап сақталды!\n\nЖаңа жауап жібере аласыз немесе уақыттың өтуін күте аласыз',
        'test_not_found': '❌ Сынақ табылмады\n\nҚайта бастаңыз',
        'test_cancelled': '❌ Сынақ тоқтатылды',
        'generating_grade': '🔄 Баға жасауда...',
        'grade_title': '📊 Баға: {grade}',
        'grade_reason_not_finnish': 'Мәтін фин тілінде емес',
        'grade_reason_off_topic': 'Мәтін тақырыпқа сәйкес емес',
        'grade_reason_rejected': 'Мәтін қабылданбады',
        'grade_reason_grade_extraction_failed': 'Бағаны шығару мүмкін емес',
        'grade_reason_error_occurred': 'Бағалау кезінде қате орын алды',
        'grade_zero_message': 'Сіз 0 баға алдыңыз. Себебі: {reason}',
        'generating_feedback': '🔄 Кеңес жасауда...',
        'feedback_title': '💡 **Кеңестер:**\n\n{feedback}',
        'generating_advice': '🔄 Кеңес жасауда...',
        'advice_title': '🎯 **Не жаттығу керек:**\n\n{advice}',
        'grade_error': '❌ Баға жасау кезінде қате\n\nКейінірек қайталап көріңіз',
        'feedback_error': '❌ Кеңес жасау кезінде қате\n\nКейінірек қайталап көріңіз',
        'advice_error': '❌ Кеңес жасау кезінде қате\n\nКейінірек қайталап көріңіз',
        'test_not_found_error': '❌ Сынақ табылмады',
        'time_expired': '⏰ Уақыт өтті!',
        'no_response_provided': '⏰ Уақыт өтті!\n\nЖауап берілмеді',
        'what_is_my_score': '📊 Менің бағам қандай?',
        'how_can_i_improve': '💡 Қалай жақсарта аламын?',
        'what_do_i_need_to_practice': '🎯 Не жаттығу керек?',
        'confirm_registration': '✅ Тіркеуді растау',
        'invite_code_prompt': '🔑 Шақыру кодын енгізіңіз:',
        'invalid_invite': '❌ Қате шақыру коды\n\nҚайталап көріңіз',
        'registration_success': '✅ Тіркеу сәтті!\n\nЕнді ботты пайдалана аласыз',
        'name_prompt': '✏️ Атыңызды енгізіңіз:',
        'name_updated': '✅ Ат жаңартылды!',
        'language_updated': '✅ Тіл өзгертілді!',
        'unknown_message': '👋 Сәлем!',
        'warning_5min': '⚠️ **Назар аударыңыз!**\n\nСынақтың аяқталуына 5 минут қалды!',
        'warning_1min': '🚨 **Шұғыл!**\n\nСынақтың аяқталуына 1 минут қалды!',
        'warning_generic': '⏰ Сынақтың аяқталуына {minutes} минут қалды!',
    }
}

def get_text(key: str, language: str = 'ru', **kwargs) -> str:
    """
    Get translated text for the given key and language.
    
    Args:
        key: Translation key
        language: Language code (ru, en, fi, kz)
        **kwargs: Format parameters for the text
        
    Returns:
        Translated text
    """
    if language not in TRANSLATIONS:
        language = 'ru'  # Default to Russian
    
    text = TRANSLATIONS[language].get(key, TRANSLATIONS['ru'].get(key, key))
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    return text
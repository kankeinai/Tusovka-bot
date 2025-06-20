from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables first
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    BOT_TOKEN: str
    DATABASE_URL_UNPOOLED: str
    OPENAI_API_KEY: str = ""  # Make optional with default empty string
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
You are an assistant for the Tusovka language school, who helps to prepare for YKI Finnish. You always give concise responses to the questions of the student. You provide feedback in the preferred language of the student."""


tests = {
    'writing_part_1': """
        Generate me topic for writing part 1 test of Finnish YKI (Epämuodollinen viesti — Неформальное сообщение). 
        Provide all instructions that are usually present on the test.
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
    'reading': 60,         
    'listening': 30,       
    'speaking': 15         
}

def get_test_time_limit(test_type: str) -> int:
    """Get time limit in minutes for a specific test type."""
    return test_time_limits.get(test_type, 30)  # Default 30 minutes
import openai
import logging
from settings import settings, system_message

# Configure OpenAI client
openai.api_key = settings.OPENAI_API_KEY

class OpenAIService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.api_available = True
        else:
            self.client = None
            self.api_available = False
            logging.warning("OpenAI API key not provided. Using fallback responses.")
    
    async def get_response(self, user_language: str, question: str, test_level: str, test_topic: str = None) -> str:
        """
        Get response from OpenAI with system message and user question.
        
        Args:
            user_language: User's preferred language (ru, en, fi, kz)
            question: The specific question or prompt
            test_topic: Optional test topic to include in the dialogue
            
        Returns:
            OpenAI response as string
        """
        if not self.api_available:
            # Fallback response when OpenAI is not available
            return get_fallback_response(user_language, question)
        
        try:
            system_msg = system_message
            
            # Build messages array
            messages = [{"role": "system", "content": system_msg}]
            
            # Add test topic if provided
            if test_topic:
                messages.append({"role": "assistant", "content": f"test topic: {test_topic}"})
              # Add the main question
            messages.append({"role": "user", "content": question + "Level of YKI is " + test_level})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=10000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return get_fallback_response(user_language, question)
    
    async def get_test_topic(self, user_language: str, test_type: str, test_level: str) -> str:
        """
        Get a specific test topic from OpenAI.
        
        Args:
            user_language: User's preferred language
            test_type: Type of test (e.g., 'writing_part_1')
            
        Returns:
            Test topic and instructions
        """
        from settings import tests
        
        if test_type not in tests:
            return "Неизвестный тип теста."

        question = tests[test_type]
        return await self.get_response(user_language, question, test_level)

def get_fallback_response(user_language: str, question: str) -> str:
    """Provide fallback responses when OpenAI is not available."""
    if "writing_part_1" in question.lower():
        return """Kirjoita teksti seuraavasta aiheesta:

AIHE: "Kotikaupunkisi parantaminen"

Kirjoita 120-180 sanaa seuraavasta aiheesta. Käytä muodollista kieltä.

Ohjeet:
- Kirjoita selkeä ja looginen teksti
- Käytä eri lausetyyppejä
- Tarkista oikeinkirjoitus ja kielioppi
- Kirjoita vähintään 120 sanaa"""
    
    return "Извините, сервис временно недоступен. Попробуйте позже."

# Create global instance
openai_service = OpenAIService() 
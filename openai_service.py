import openai
import logging
import re
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
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return get_fallback_response(user_language, question)
    
    async def get_numeric_grade(self, user_language: str, question: str, test_level: str, test_topic: str = None) -> int:
        """
        Get a numeric grade from OpenAI using function calling to ensure only a number is returned.
        
        Args:
            user_language: User's preferred language
            question: The grading question
            test_level: YKI test level
            test_topic: Optional test topic
            
        Returns:
            Numeric grade (0-6 for YKI)
        """
        if not self.api_available:
            # Fallback grade when OpenAI is not available
            return 3
        
        try:
            # Define the tool schema for grade output
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "provide_grade",
                        "description": "Provide only the numerical grade according to YKI grading scale (0-6)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "grade": {
                                    "type": "integer",
                                    "description": "YKI grade from 0 to 6",
                                    "minimum": 0,
                                    "maximum": 6
                                }
                            },
                            "required": ["grade"]
                        }
                    }
                }
            ]
            
            # Build messages array
            messages = [{"role": "system", "content": "You are a YKI exam grader. Provide only numerical grades from 0-6 scale. No explanations, no text, just the grade number."}]
            
            # Add test topic if provided
            if test_topic:
                messages.append({"role": "assistant", "content": f"Test topic: {test_topic}"})
            
            # Add the main question
            messages.append({"role": "user", "content": question + " Level of YKI is " + test_level})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "provide_grade"}},
                temperature=0.3,  # Lower temperature for more consistent grading
                max_tokens=50
            )
            
            # Extract the grade from tool call
            if response.choices[0].message.tool_calls:
                import json
                tool_call = response.choices[0].message.tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                grade = function_args.get("grade", 3)
                return max(0, min(6, grade))  # Ensure grade is between 0-6
            
            # Fallback if tool call fails
            return 3
            
        except Exception as e:
            logging.error(f"OpenAI API error in get_numeric_grade: {e}")
            return 3
    
    async def get_numeric_grade_fallback(self, user_language: str, question: str, test_level: str, test_topic: str = None) -> int:
        """
        Alternative method to get numeric grade using regex extraction as fallback.
        
        Args:
            user_language: User's preferred language
            question: The grading question
            test_level: YKI test level
            test_topic: Optional test topic
            
        Returns:
            Numeric grade (0-6 for YKI)
        """
        if not self.api_available:
            return 3
        
        try:
            # Build messages array with strict instructions
            messages = [
                {"role": "system", "content": "You are a YKI exam grader. Respond with ONLY a single number from 0 to 6. No text, no explanations, no punctuation. Just the number."},
                {"role": "user", "content": question + " Level of YKI is " + test_level}
            ]
            
            # Add test topic if provided
            if test_topic:
                messages.insert(1, {"role": "assistant", "content": f"Test topic: {test_topic}"})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,  # Very low temperature for consistent output
                max_tokens=10     # Very short response
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract number using regex
            number_match = re.search(r'\b([0-6])\b', content)
            if number_match:
                grade = int(number_match.group(1))
                return grade
            
            # If no number found, try to extract any digit and clamp to 0-6
            any_number = re.search(r'\b(\d+)\b', content)
            if any_number:
                grade = int(any_number.group(1))
                return max(0, min(6, grade))
            
            # Fallback
            return 3
            
        except Exception as e:
            logging.error(f"OpenAI API error in get_numeric_grade_fallback: {e}")
            return 3
    
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
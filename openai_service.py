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
    
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text using OpenAI.
        """
        if not self.api_available:
            return "unknown"
        
        try:
            prompt = f"What language is this text written in? Respond with only the language name.\n\n{text}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a language detector. Respond with only the language name in English."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=20
            )
            
            answer = response.choices[0].message.content.strip().lower()
            logging.info(f"Language detected: {answer} for text: {text[:50]}...")
            return answer
            
        except Exception as e:
            logging.error(f"Language detection error: {e}")
            return "unknown"
    
    async def is_finnish(self, text: str) -> bool:
        """
        Check if the text is written in Finnish.
        """
        if not text or len(text.strip()) < 10:
            return False
        language = await self.detect_language(text)
        finnish_indicators = [
            "finnish", "suomi", "suomen", "suomalainen", "suomenkielinen"
        ]
        return any(indicator in language for indicator in finnish_indicators)
    
    async def get_response(self, user_language: str, question: str, test_level: str, test_topic: str = None, tokens: int = 250) -> str:
        """
        Get response from OpenAI with system message and user question.
        """
        if not self.api_available:
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
                temperature=0.5,
                max_tokens=tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return get_fallback_response(user_language, question)
    
    async def get_numeric_grade(self, user_language: str, question: str, test_level: str, test_topic: str = None) -> tuple[int, str]:
        """
        Get a numeric grade from OpenAI using the check_and_grade pipeline.
        Returns (grade, reason_code) tuple. Reason_code is a translation key or empty string.
        """
        if not self.api_available:
            return (3, "")  # Fallback grade, no reason
        
        try:
            # Extract the response text from the question for language detection

            # Clean up the response text (remove quotes, extra spaces)
            response_text = question.strip('"').strip("'").strip()
            
            # Use the check_and_grade pipeline
            if test_topic and response_text:
                result = await self.check_and_grade(test_topic, response_text)
                logging.info(f"result: {result}")
                if result["status"] == "rejected":
                    logging.info(f"Text rejected: {result['reason']}")
                    if "not in Finnish" in result["reason"]:
                        return (0, "not_finnish")
                    elif "off-topic" in result["reason"]:
                        return (0, "off_topic")
                    else:
                        return (0, "rejected")
                else:
                    return (result["evaluation"][0], "")
            
            # Fallback to original method if no topic provided or no response text extracted
            return (3, "")  # Default fallback
            
        except Exception as e:
            logging.error(f"Error in get_numeric_grade: {e}")
            return (0, "error_occurred")
    
    async def get_test_topic(self, user_language: str, test_type: str, test_level: str) -> str:
        """
        Get a specific test topic from OpenAI.
        """
        from settings import tests
        
        if test_type not in tests:
            return "Неизвестный тип теста."

        question = tests[test_type]
        return await self.get_response(user_language, question, test_level)
    
    async def check_topic_relevance(self, task: str, essay: str) -> bool:
        """
        Check if the essay matches the given task topic.
        Returns True if on-topic or partially relevant.
        """
        if not self.api_available:
            return True  # Assume relevant if API not available
        
        try:
            prompt = f"""
Tarkista, vastaako seuraava teksti annettua tehtävän aihetta.

Tehtävän aihe:
"{task}"

Teksti:
"{essay}"

Arvioi relevanssi seuraavasti:
- Jos teksti käsittelee aihetta suoraan tai sivuaa sitä merkittävästi, vastaa "kyllä"
- Jos teksti on vain etäisesti aiheeseen liittyvä, vastaa "osittain"
- Jos teksti ei liity aiheeseen lainkaan, vastaa "ei"

Vastaa vain yhdellä sanalla: kyllä, osittain tai ei."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Olet kielitestien tarkistaja. Ole kohtuullinen arvioinnissa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            answer = response.choices[0].message.content.strip().lower()
            
            # Accept both "kyllä" and "osittain" as relevant
            return answer in ["kyllä", "osittain"]
            
        except Exception as e:
            logging.error(f"Topic relevance check error: {e}")
            return True  # Assume relevant on error to avoid false rejections

    async def get_yki_evaluation(self, task: str, essay: str) -> str:
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
        messages.append({"role": "assistant", "content": f"Test topic: {task}"})
        
        # Add the main question
        messages.append({"role": "user", "content": essay })

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "provide_grade"}},
            temperature=0.3,
            max_tokens=50
        )
        try:
            # Extract the grade from tool call
            if response.choices[0].message.tool_calls:
                import json
                tool_call = response.choices[0].message.tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                grade = function_args.get("grade", 3)
                return (max(0, min(6, grade)), "yki evaluation")
        except Exception as e:
            logging.error(f"Error in get_yki_evaluation: {e}")
            return (0, f"Error: {str(e)}")
        

    async def check_and_grade(self, task: str, essay: str) -> dict:
        """
        Full pipeline: language check, topic relevance, and YKI evaluation.
        Returns a dict with status and feedback.
        """
        # Language check
        if not await self.is_finnish(essay):
            return {"status": "rejected", "reason": "Text is not in Finnish."}
        
        # Topic relevance check with detailed feedback
        topic_relevant = await self.check_topic_relevance(task, essay)
        if not topic_relevant:
            return {
                "status": "rejected", 
                "reason": f"Text is off-topic. Please write about the given topic."
            }
        
        # YKI evaluation
        yki_feedback = await self.get_yki_evaluation(task, essay)
        return {"status": "accepted", "evaluation": yki_feedback}

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

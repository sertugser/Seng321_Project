import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API Key from environment variables
API_KEY = os.getenv('GEMINI_API_KEY')

if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found! Please check your .env file.")
    print("Make sure .env file is in the project root directory and contains: GEMINI_API_KEY=your_key_here")
else:
    genai.configure(api_key=API_KEY)
    print(f"Gemini API configured successfully. API Key length: {len(API_KEY)}")

class AIService:
    @staticmethod
    def evaluate_writing(text_content):
        """
        Analyzes student writing using the Gemini AI model.
        Returns a JSON object containing score, errors, and feedback.
        """
        if not API_KEY:
            print("ERROR: Cannot evaluate writing - GEMINI_API_KEY is not set!")
            return {
                "score": 0,
                "grammar_errors": ["API key not configured. Please check your .env file."],
                "vocabulary_suggestions": [],
                "general_feedback": "Could not process AI request - API key missing."
            }
        
        if not text_content or len(text_content.strip()) == 0:
            print("ERROR: Empty text content provided for analysis")
            return {
                "score": 0,
                "grammar_errors": ["No text content provided for analysis."],
                "vocabulary_suggestions": [],
                "general_feedback": "Please provide some text to analyze."
            }
        
        # List available models and use the first one that supports generateContent
        model = None
        try:
            print("Fetching available models from API...")
            available_models = genai.list_models()
            
            # Find models that support generateContent
            supported_models = []
            for m in available_models:
                if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                    model_name = m.name.replace('models/', '')
                    supported_models.append(model_name)
                    print(f"Found supported model: {model_name}")
            
            if not supported_models:
                print("No models with generateContent support found. Trying common model names...")
                # Fallback to common names
                supported_models = ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash']
            
            # Try to use preferred models first
            preferred = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
            model_name = None
            
            for pref in preferred:
                if pref in supported_models:
                    model_name = pref
                    break
            
            if not model_name and supported_models:
                model_name = supported_models[0]
            
            if model_name:
                print(f"Attempting to use model: {model_name}")
                model = genai.GenerativeModel(model_name)
                print(f"Successfully initialized model: {model_name}")
            else:
                raise Exception("No available models found")
                
        except Exception as e:
            print(f"Error fetching models: {e}")
            print("Trying direct model initialization with common names...")
            # Fallback: try common model names directly
            fallback_names = ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash']
            for model_name in fallback_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    print(f"Successfully initialized model: {model_name}")
                    break
                except Exception as e2:
                    print(f"Failed {model_name}: {str(e2)}")
                    continue
        
        if not model:
            return {
                "score": 0,
                "grammar_errors": ["Could not initialize any Gemini model. Please check your API key and available models."],
                "vocabulary_suggestions": [],
                "general_feedback": "Could not process AI request - model initialization failed. Please check your API key."
            } 
        
        prompt = f"""
        You are an experienced English teacher. Analyze the following student writing submission:
        
        "{text_content}"
        
        Please provide the output strictly in valid JSON format with the following keys:
        - score: An integer between 0 and 100 representing the quality.
        - grammar_errors: A list of strings, each describing a specific grammar mistake found.
        - vocabulary_suggestions: A list of strings suggesting better vocabulary usage.
        - general_feedback: A supportive short paragraph summarizing the student's performance.
        
        Do not use markdown formatting (like ```json). Just return the raw JSON object.
        """
        
        try:
            print(f"Calling Gemini API with text length: {len(text_content)} characters")
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                print("ERROR: Empty response from Gemini API")
                return {
                    "score": 0,
                    "grammar_errors": ["Empty response from AI service."],
                    "vocabulary_suggestions": [],
                    "general_feedback": "Could not process AI request - empty response."
                }
            
            # Clean potential markdown formatting from the response
            clean_text = response.text.strip().replace('```json', '').replace('```', '')
            print(f"Received response from API, length: {len(clean_text)}")
            
            result = json.loads(clean_text)
            print(f"Successfully parsed JSON response. Score: {result.get('score', 'N/A')}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Response text was: {response.text if 'response' in locals() else 'No response'}")
            return {
                "score": 0,
                "grammar_errors": [f"JSON parsing error: {str(e)}"],
                "vocabulary_suggestions": [],
                "general_feedback": "Could not parse AI response."
            }
        except Exception as e:
            print(f"AI Service Execution Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "score": 0,
                "grammar_errors": [f"AI error: {str(e)}"],
                "vocabulary_suggestions": [],
                "general_feedback": f"Could not process AI request: {str(e)}"
            }
    
    @staticmethod
    def evaluate_speaking(audio_file_path):
        """
        Analyzes student speaking from audio file.
        Returns a JSON object containing pronunciation_score, fluency_score, and feedback.
        This is a mock implementation for student project purposes.
        """
        import random
        import os
        
        if not audio_file_path or not os.path.exists(audio_file_path):
            return {
                "pronunciation_score": 0,
                "fluency_score": 0,
                "feedback": "Audio file not found or invalid.",
                "tips": ["Please ensure the audio file is valid and try again."]
            }
        
        # Get file size to simulate some analysis
        file_size = os.path.getsize(audio_file_path)
        
        # Mock analysis: Generate realistic scores based on file characteristics
        # In a real implementation, this would use speech recognition and NLP
        base_score = 70
        variation = random.randint(-15, 20)
        
        pronunciation_score = max(0, min(100, base_score + variation))
        fluency_score = max(0, min(100, base_score + variation + random.randint(-5, 5)))
        
        # Generate feedback based on scores
        if pronunciation_score >= 85:
            pronunciation_feedback = "Excellent pronunciation! Your articulation is clear and accurate."
        elif pronunciation_score >= 70:
            pronunciation_feedback = "Good pronunciation overall. Some words could be clearer."
        elif pronunciation_score >= 55:
            pronunciation_feedback = "Pronunciation needs improvement. Focus on clear articulation."
        else:
            pronunciation_feedback = "Pronunciation requires significant practice. Consider working with a tutor."
        
        if fluency_score >= 85:
            fluency_feedback = "Great fluency! Your speech flows naturally."
        elif fluency_score >= 70:
            fluency_feedback = "Good fluency. Try to reduce pauses and hesitations."
        elif fluency_score >= 55:
            fluency_feedback = "Fluency needs work. Practice speaking more smoothly."
        else:
            fluency_feedback = "Fluency needs significant improvement. Practice reading aloud regularly."
        
        # Generate tips
        tips = []
        if pronunciation_score < 80:
            tips.append("Practice difficult words slowly, then gradually increase speed")
            tips.append("Record yourself and compare with native speakers")
        if fluency_score < 80:
            tips.append("Read aloud daily to improve speech flow")
            tips.append("Practice speaking without long pauses")
        if pronunciation_score >= 80 and fluency_score >= 80:
            tips.append("Keep up the excellent work!")
            tips.append("Continue practicing to maintain your level")
        
        general_feedback = f"{pronunciation_feedback} {fluency_feedback} Overall, your speaking shows potential for improvement with consistent practice."
        
        return {
            "pronunciation_score": round(pronunciation_score, 1),
            "fluency_score": round(fluency_score, 1),
            "feedback": general_feedback,
            "tips": tips
        }
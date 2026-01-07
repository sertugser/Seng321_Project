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
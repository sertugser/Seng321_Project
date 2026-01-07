import pytesseract
from PIL import Image
import os
from dotenv import load_dotenv
load_dotenv()

TESSERACT_PATH = os.getenv('TESSERACT_PATH', 'tesseract') 
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

class OCRService:
    @staticmethod
    def extract_text_from_image(image_path):
        """
        Processes an image file to extract handwritten or printed text.
        """
        try:
            # Check if file exists before processing
            if not os.path.exists(image_path):
                print(f"Error: File not found at {image_path}")
                return None

            # Open image using Pillow
            img = Image.open(image_path)
            
            # Convert image to string
            # Using 'eng' for English language recognition
            text = pytesseract.image_to_string(img, lang='eng')
            
            return text.strip()
        except Exception as e:
            # Print detailed error to terminal for debugging
            print(f"OCR System Error: {e}")
            if "tesseract" in str(e).lower():
                print("Note: Make sure Tesseract OCR is installed and TESSERACT_PATH is set correctly in .env file")
            return None
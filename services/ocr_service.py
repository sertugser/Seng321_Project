import io
import os
import pytesseract
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

TESSERACT_PATH = os.getenv('TESSERACT_PATH', 'tesseract') 
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

class OCRService:
    @staticmethod
    def extract_text_from_image(image_path):
        """
        Processes an image or PDF file to extract handwritten or printed text.
        """
        try:
            # Check if file exists before processing
            if not os.path.exists(image_path):
                print(f"Error: File not found at {image_path}")
                return None

            _, ext = os.path.splitext(image_path)
            ext = ext.lower()

            if ext == '.pdf':
                return OCRService._extract_text_from_pdf(image_path)

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

    @staticmethod
    def _extract_text_from_pdf(pdf_path):
        try:
            import fitz  # PyMuPDF
        except Exception as e:
            print(f"OCR PDF Error: PyMuPDF is not available ({e})")
            return None

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"OCR PDF Error: Failed to open PDF ({e})")
            return None

        extracted_pages = []
        for page in doc:
            page_text = ''
            try:
                page_text = (page.get_text() or '').strip()
            except Exception:
                page_text = ''

            if not page_text:
                try:
                    # Render page at higher DPI for better OCR results
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    page_text = pytesseract.image_to_string(img, lang='eng').strip()
                except Exception as e:
                    print(f"OCR PDF Error: Failed OCR on page {page.number + 1} ({e})")
                    page_text = ''

            if page_text:
                extracted_pages.append(page_text)

        doc.close()
        return "\n\n".join(extracted_pages).strip() if extracted_pages else None

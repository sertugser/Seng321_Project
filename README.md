# 🎓 AI-Driven Student Learning Dashboard

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-white?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Latest-003B57?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini_1.5_Flash-orange?style=for-the-badge&logo=google-gemini)](https://aistudio.google.com/)

An intelligent, full-stack English learning ecosystem designed to enhance student writing and speaking skills through **Artificial Intelligence** and **OCR Technology**.

---

## ✨ Key Features

### 🤖 Smart Evaluation
* **AI Writing Analysis:** Leverages **Gemini 1.5 Flash** to provide instant feedback on grammar, vocabulary, and overall quality.
* **OCR Integration:** Uses **Tesseract OCR** to digitize and grade handwritten assignments from image uploads.

### 📊 Comprehensive Dashboards
* **Student Hub:** View real-time performance charts, track grade history, and manage personal learning goals.
* [cite_start]**Instructor Portal:** Centralized management to monitor class progress, review all student submissions, and manually adjust grades. [cite: 1]

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | Python / Flask |
| **Database** | SQLite / SQLAlchemy |
| **AI/ML** | Google Gemini API |
| **OCR** | Pytesseract & Pillow |
| **Frontend** | HTML5, CSS3, Jinja2 |

---

## 🚀 Getting Started

### 1. Requirements
* **Python 3.10+** (Check with `python --version`)
* **Tesseract OCR** installed on your local machine
  - **Windows:** Download from [GitHub Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki) and install
  - **Linux:** `sudo apt-get install tesseract-ocr` (Ubuntu/Debian) or `sudo yum install tesseract` (CentOS/RHEL)
  - **Mac:** `brew install tesseract`

### 2. Installation & Setup

#### Step 1: Clone the Repository
```bash
git clone <your-repository-url>
cd <project-folder>
```

#### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all required packages
python -m pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables
Create a `.env` file in the project root and add your actual values:
   ```env
   # Generate a secret key (run this command):
   # python -c "import secrets; print(secrets.token_hex(16))"
   SECRET_KEY=your-generated-secret-key-here
   
   # Get your Gemini API key from: https://aistudio.google.com/app/apikey
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   
   # Tesseract path (only needed if not in system PATH)
   # Windows example:
   TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
   # Linux/Mac: Usually leave empty if installed via package manager
   # TESSERACT_PATH=
   ```

#### Step 5: Run the Application
```bash
python app.py
```

The application will:
- Create the database automatically on first run
- Create necessary directories (static/uploads)
- Start the Flask development server on `http://127.0.0.1:5000`

### 3. First Time Setup Notes
- The database (`site.db`) will be created automatically when you first run the app
- You can register a new account from the login page
- To create an instructor account, register with role "Instructor"

### 4. Troubleshooting

**Error: "GEMINI_API_KEY not found"**
- Make sure you created a `.env` file (copy from `.env.example`)
- Check that your API key is correct

**Error: "Tesseract not found"**
- Install Tesseract OCR on your system
- If installed but not in PATH, set `TESSERACT_PATH` in `.env` file

**Error: "Module not found"**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again
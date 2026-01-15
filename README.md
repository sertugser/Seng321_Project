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
cd Seng321_Project-main
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
1. Copy the example environment file:
   ```bash
   # On Windows (PowerShell):
   Copy-Item .env.example .env
   
   # On Linux/Mac:
   cp .env.example .env
   ```

2. Edit the `.env` file and add your actual values:
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

### 3. Admin Account Setup

To create an admin account, you have several options:

#### Option 1: Using the Admin Creation Script (Recommended)
1. Navigate to the project directory in Terminal/PowerShell
2. Run the script:
   ```bash
   python create_admin.py
   ```
3. Enter the required information:
   - Username
   - Email address
   - Password (minimum 6 characters)
   - Confirm Password

#### Option 2: Modify Existing User to Admin
If you already have a user account:
1. Run the application:
   ```bash
   python app.py
   ```
2. Navigate to `/admin/users` page (if another admin exists)
3. Find your user and click "Edit"
4. Change the role to "Admin" and save

#### Option 3: Create Admin via Python Console
Using Python console:
```python
from app import create_app
from models.database import db
from models.entities import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin = User(
        username='admin',
        email='admin@example.com',
        password=generate_password_hash('your_password', method='pbkdf2:sha256'),
        role='Admin'
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")
```

### 4. Admin Panel Access

1. Start the application:
   ```bash
   python app.py
   ```

2. Navigate to the login page:
   ```
   http://127.0.0.1:5000/login
   ```

3. Enter your admin email and password

4. After login, you will be automatically redirected to the admin dashboard

### 5. Admin Panel Features

#### User Management (FR17)
- View all users
- Create new users
- Edit user information
- Delete users
- Filter by role (Student, Instructor, Admin)

#### Course & Enrollment Management (FR17)
- View and manage courses
- Enroll students in courses
- Manage enrollment statuses (active, completed, dropped)
- View course enrollments

#### Platform Settings (FR18)
- Configure platform-wide settings
- Manage setting keys and values
- Add setting descriptions

#### AI Integration Management (FR18)
- Configure external AI services
- Manage API keys
- Activate/deactivate integrations
- Configure API endpoints

#### LMS Integration Management (FR18, FR20)
- Configure LMS integrations (Canvas, Moodle, Blackboard)
- Manage API credentials
- Enable/disable grade synchronization
- Sync grades to external LMS platforms

### 6. First Time Setup Notes
- The database (`site.db`) will be created automatically when you first run the app
- You can register a new account from the login page
- To create an instructor account, register with role "Instructor"
- Admin panel access is restricted to users with 'Admin' role
- Keep your admin password strong and change it regularly for security

### 7. Troubleshooting

**Error: "GEMINI_API_KEY not found"**
- Make sure you created a `.env` file (copy from `.env.example`)
- Check that your API key is correct

**Error: "Tesseract not found"**
- Install Tesseract OCR on your system
- If installed but not in PATH, set `TESSERACT_PATH` in `.env` file

**Error: "Module not found"**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again
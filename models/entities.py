from models.database import db
from datetime import datetime
from flask_login import UserMixin

# --- 1. User Entity ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Student') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    submissions = db.relationship('Submission', backref='student', lazy=True)

    # Optional profile fields (added for profile & settings pages)
    profile_image = db.Column(db.String(200), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    university = db.Column(db.String(120), nullable=True)
    grade = db.Column(db.String(50), nullable=True)
    teacher = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    education_status = db.Column(db.String(80), nullable=True)

    # Optional AI preference fields (used on settings page)
    ai_tone = db.Column(db.String(20), nullable=True)
    ai_speed = db.Column(db.Float, nullable=True)
    weekly_report = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<User {self.username}>'

# --- 2. LearningActivity Entity ---
class LearningActivity(db.Model):
    __tablename__ = 'learning_activity'
    id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False) 
    activity_type = db.Column(db.String(20), nullable=False) # WRITING, SPEAKING, QUIZ
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    instructor = db.relationship('User', backref=db.backref('created_activities', lazy=True))

# --- 3. Submission Entity ---
class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('learning_activity.id'), nullable=True)
    submission_type = db.Column(db.String(20), nullable=False) 
    file_path = db.Column(db.String(200), nullable=True) 
    text_content = db.Column(db.Text, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.relationship('Grade', backref='submission', uselist=False, cascade="all, delete-orphan")

# --- 4. Grade Entity (Speaking Metrics Added) ---
class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    score = db.Column(db.Float, nullable=False) 
    grammar_feedback = db.Column(db.Text, nullable=True)
    vocabulary_feedback = db.Column(db.Text, nullable=True)
    general_feedback = db.Column(db.Text, nullable=True)
    # Speaking Metrics [New]
    pronunciation_score = db.Column(db.Float, nullable=True)
    fluency_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- 5. LearningGoal Entity (UC7) ---
class LearningGoal(db.Model):
    __tablename__ = 'learning_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_name = db.Column(db.String(100), nullable=False) # e.g., "Improve Pronunciation"
    target_value = db.Column(db.Integer, default=100)
    current_value = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- 6. Quiz Entity ---
class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_title = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)

# --- 7. Question Entity ---
class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=True)
    option_d = db.Column(db.String(200), nullable=True)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    category = db.Column(db.String(50), nullable=True)  # 'grammar', 'vocabulary', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
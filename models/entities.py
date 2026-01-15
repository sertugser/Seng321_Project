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
    quiz_category = db.Column(db.String(50), nullable=True)  # grammar, vocabulary, reading, etc.
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
    instructor_approved = db.Column(db.Boolean, default=False, nullable=False)  # False = Pending, True = Graded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- 5. LearningGoal Entity (UC7) ---
class LearningGoal(db.Model):
    __tablename__ = 'learning_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_name = db.Column(db.String(100), nullable=False) # e.g., "Improve Pronunciation"
    category = db.Column(db.String(50), nullable=True, default='General')
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

# --- 7. QuizDetail Entity (store per-question results) ---
class QuizDetail(db.Model):
    __tablename__ = 'quiz_details'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.String(5), nullable=True)
    correct_answer = db.Column(db.String(5), nullable=True)
    is_correct = db.Column(db.Boolean, default=False)

# --- 8. Question Entity ---
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

# --- 9. Course Entity ---
class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "ENG101"
    description = db.Column(db.Text, nullable=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    instructor = db.relationship('User', backref=db.backref('taught_courses', lazy=True))

# --- 10. Enrollment Entity (Many-to-Many: User <-> Course) ---
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active', 'completed', 'dropped'
    student = db.relationship('User', backref=db.backref('enrollments', lazy=True))
    course = db.relationship('Course', backref=db.backref('enrollments', lazy=True))
    
    # Ensure one enrollment per student per course
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_student_course'),)

# --- 11. PlatformSettings Entity ---
class PlatformSettings(db.Model):
    __tablename__ = 'platform_settings'
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=True)
    setting_type = db.Column(db.String(50), nullable=False)  # 'string', 'integer', 'boolean', 'json'
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updater = db.relationship('User', backref=db.backref('updated_settings', lazy=True))

# --- 12. AIIntegration Entity ---
class AIIntegration(db.Model):
    __tablename__ = 'ai_integrations'
    id = db.Column(db.Integer, primary_key=True)
    integration_name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'gemini', 'openai'
    api_key = db.Column(db.Text, nullable=True)  # Encrypted or stored securely
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    api_endpoint = db.Column(db.String(200), nullable=True)
    configuration = db.Column(db.Text, nullable=True)  # JSON string for additional config
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updater = db.relationship('User', backref=db.backref('updated_ai_integrations', lazy=True))

# --- 13. LMSIntegration Entity (FR20, UC15) ---
class LMSIntegration(db.Model):
    __tablename__ = 'lms_integrations'
    id = db.Column(db.Integer, primary_key=True)
    lms_type = db.Column(db.String(50), nullable=False)  # 'canvas', 'moodle', 'blackboard'
    lms_name = db.Column(db.String(100), nullable=False)
    api_url = db.Column(db.String(200), nullable=False)  # LMS API base URL
    api_key = db.Column(db.Text, nullable=True)  # API key or token
    api_secret = db.Column(db.Text, nullable=True)  # API secret (if needed)
    course_id = db.Column(db.String(100), nullable=True)  # LMS course ID for grade sync
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    sync_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Enable/disable grade sync
    last_sync_at = db.Column(db.DateTime, nullable=True)
    configuration = db.Column(db.Text, nullable=True)  # JSON string for additional config
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updater = db.relationship('User', backref=db.backref('updated_lms_integrations', lazy=True))

# --- 14. AdaptiveInsight Entity (UC17) ---
class AdaptiveInsight(db.Model):
    __tablename__ = 'adaptive_insights'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    insight_type = db.Column(db.String(50), nullable=False)  # 'performance', 'recommendation', 'prediction'
    insight_text = db.Column(db.Text, nullable=False)
    area_focus = db.Column(db.String(50), nullable=True)  # 'speaking', 'writing', 'quiz', 'handwritten'
    confidence_score = db.Column(db.Float, nullable=True)  # 0.0 to 1.0
    recommendation_action = db.Column(db.String(200), nullable=True)  # Suggested action
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # When this insight becomes stale
    user = db.relationship('User', backref=db.backref('adaptive_insights', lazy=True))
import os
from datetime import datetime 
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import docx 
from functools import wraps

# Project internal imports
from config import Config
from models.database import db
from models.entities import User, Submission, Grade, LearningActivity, LearningGoal, Quiz, Question
from services.ai_service import AIService
from services.ocr_service import OCRService
from services.grading_service import GradingService
from services.submission_service import SubmissionService
from services.quiz_service import QuizService
from services.notification_service import NotificationService
from services.activity_service import ActivityService
from services.feedback_service import FeedbackService
from services.goal_service import GoalService
from services.stats_service import StatsService
from services.report_service import ReportService
from repositories.quiz_repository import QuizRepository
from repositories.grade_repository import GradeRepository
from repositories.activity_repository import ActivityRepository
from repositories.goal_repository import GoalRepository
from repositories.feedback_repository import FeedbackRepository

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database
    db.init_app(app)

    # Login Manager Setup
    login_manager = LoginManager()
    login_manager.login_view = 'login' 
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- GLOBAL USER INJECTION ---
    @app.context_processor
    def inject_user():
        return dict(user=current_user)

    # Configure Upload Folder
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

    # Create Database Tables
    with app.app_context():
        db.create_all()

        # --- Ensure new optional User columns exist (safe for existing SQLite DB) ---
        from sqlalchemy import text
        insp = db.inspect(db.engine)
        existing_cols = {col['name'] for col in insp.get_columns('users')}

        # Helper to add column only if it does not exist
        def _add_column_if_missing(column_name: str, ddl: str):
            if column_name not in existing_cols:
                db.session.execute(text(f"ALTER TABLE users ADD COLUMN {ddl}"))
                db.session.commit()

        # New profile / personal info fields
        _add_column_if_missing('profile_image', 'profile_image VARCHAR(200)')
        _add_column_if_missing('bio', 'bio TEXT')
        _add_column_if_missing('university', 'university VARCHAR(120)')
        _add_column_if_missing('grade', 'grade VARCHAR(50)')
        _add_column_if_missing('teacher', 'teacher VARCHAR(120)')
        _add_column_if_missing('phone', 'phone VARCHAR(50)')
        _add_column_if_missing('education_status', 'education_status VARCHAR(80)')

        # AI preference fields
        _add_column_if_missing('ai_tone', 'ai_tone VARCHAR(20)')
        _add_column_if_missing('ai_speed', 'ai_speed FLOAT')
        _add_column_if_missing('weekly_report', 'weekly_report BOOLEAN DEFAULT 1')

    # --- AUTHENTICATION CHECK & CACHE CONTROL ---
    @app.before_request
    def check_user_auth():
        public_routes = ['login', 'register', 'static', 'privacy', 'terms']
        if not current_user.is_authenticated and request.endpoint not in public_routes:
            return redirect(url_for('login'))

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    
    # Role Based Access Decorator
    def role_required(role):
        def wrapper(fn):
            @wraps(fn)
            @login_required
            def decorated_view(*args, **kwargs):
                if current_user.role != role:
                    flash(f"Access Denied: Only {role}s are authorized.", "danger")
                    return redirect(url_for('dashboard'))
                return fn(*args, **kwargs)
            return decorated_view
        return wrapper

    # --- AUTH ROUTES ---
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['POST'])
    def register():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Student') 
        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for('login'))
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated: return redirect(url_for('dashboard'))
        if request.method == 'POST':
            user = User.query.filter_by(email=request.form.get('email')).first()
            if user and check_password_hash(user.password, request.form.get('password')):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash("Invalid credentials.", "danger")
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'Instructor':
            return redirect(url_for('instructor_dashboard'))
        
        from datetime import timedelta
        
        # Get all submissions
        submissions = Submission.query.filter_by(student_id=current_user.id).order_by(Submission.created_at.asc()).all()
        
        # Calculate Speaking Score (average of pronunciation_score and fluency_score)
        speaking_subs = [s for s in submissions if s.submission_type == 'SPEAKING' and s.grade]
        speaking_score = 0.0
        if speaking_subs:
            scores = []
            for sub in speaking_subs:
                if sub.grade.pronunciation_score and sub.grade.fluency_score:
                    scores.append((sub.grade.pronunciation_score + sub.grade.fluency_score) / 2)
            speaking_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        
        # Calculate Writing Score (average of writing submissions)
        writing_subs = [s for s in submissions if s.submission_type == 'WRITING' and s.grade]
        writing_score = round(sum(s.grade.score for s in writing_subs) / len(writing_subs), 1) if writing_subs else 0.0
        
        # Calculate Quiz Progress
        all_quizzes = Quiz.query.filter_by(user_id=current_user.id).all()
        completed_quizzes = len(all_quizzes)
        quiz_progress = completed_quizzes  # Can be enhanced with total available quizzes
        
        # Calculate Current Streak (consecutive days with submissions)
        current_streak = 0
        if submissions:
            # Get unique submission dates
            submission_dates = set()
            for sub in submissions:
                submission_dates.add(sub.created_at.date())
            
            # Calculate streak backwards from today
            today = datetime.utcnow().date()
            check_date = today
            while check_date in submission_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        
        # Calculate Weekly Goal Progress
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Monday of current week
        weekly_submissions = [s for s in submissions if s.created_at.date() >= week_start]
        weekly_goal_current = len(weekly_submissions)
        weekly_goal_target = 5  # Default weekly goal
        weekly_goal_percentage = min(100, int((weekly_goal_current / weekly_goal_target) * 100)) if weekly_goal_target > 0 else 0
        weekly_goal_remaining = max(0, weekly_goal_target - weekly_goal_current)
        
        # Get recent submissions for the chart
        recent_submissions = submissions[-10:] if len(submissions) > 10 else submissions
        
        # Calculate Handwritten Score
        handwritten_subs = [s for s in submissions if s.submission_type == 'HANDWRITTEN' and s.grade]
        
        # Prepare multi-line chart data: Speaking, Writing, Quiz, Handwritten scores by date
        from collections import defaultdict
        chart_data = {
            'dates': [],
            'speaking_scores': [],
            'writing_scores': [],
            'quiz_scores': [],
            'handwritten_scores': []
        }
        
        # Get Handwritten submissions
        handwritten_subs = [s for s in submissions if s.submission_type == 'HANDWRITTEN' and s.grade]
        
        # Collect all dates from submissions and quizzes
        all_dates = set()
        
        # Speaking submissions with dates
        for sub in speaking_subs:
            if sub.grade and sub.grade.pronunciation_score is not None and sub.grade.fluency_score is not None:
                date_key = sub.created_at.date()
                all_dates.add(date_key)
        
        # Writing submissions with dates
        for sub in writing_subs:
            if sub.grade and sub.grade.score is not None:
                date_key = sub.created_at.date()
                all_dates.add(date_key)
        
        # Handwritten submissions with dates
        for sub in handwritten_subs:
            if sub.grade and sub.grade.score is not None:
                date_key = sub.created_at.date()
                all_dates.add(date_key)
        
        # Quiz submissions with dates
        for quiz in all_quizzes:
            if quiz.date_taken and quiz.score is not None:
                date_key = quiz.date_taken.date() if isinstance(quiz.date_taken, datetime) else quiz.date_taken
                all_dates.add(date_key)
        
        # Sort dates
        sorted_dates = sorted(all_dates)
        
        # Create date-indexed dictionaries
        speaking_by_date = {}
        writing_by_date = {}
        handwritten_by_date = {}
        quiz_by_date = {}
        
        for sub in speaking_subs:
            if sub.grade and sub.grade.pronunciation_score is not None and sub.grade.fluency_score is not None:
                date_key = sub.created_at.date()
                score = (sub.grade.pronunciation_score + sub.grade.fluency_score) / 2
                if date_key not in speaking_by_date:
                    speaking_by_date[date_key] = []
                speaking_by_date[date_key].append(score)
        
        for sub in writing_subs:
            if sub.grade and sub.grade.score is not None:
                date_key = sub.created_at.date()
                if date_key not in writing_by_date:
                    writing_by_date[date_key] = []
                writing_by_date[date_key].append(sub.grade.score)
        
        for sub in handwritten_subs:
            if sub.grade and sub.grade.score is not None:
                date_key = sub.created_at.date()
                if date_key not in handwritten_by_date:
                    handwritten_by_date[date_key] = []
                handwritten_by_date[date_key].append(sub.grade.score)
        
        for quiz in all_quizzes:
            if quiz.date_taken and quiz.score is not None:
                date_key = quiz.date_taken.date() if isinstance(quiz.date_taken, datetime) else quiz.date_taken
                if date_key not in quiz_by_date:
                    quiz_by_date[date_key] = []
                quiz_by_date[date_key].append(quiz.score)
        
        # Average scores per date and build chart data
        for date in sorted_dates:
            chart_data['dates'].append(date.strftime('%d %b'))
            
            # Speaking: average if multiple submissions on same date
            if date in speaking_by_date:
                chart_data['speaking_scores'].append(round(sum(speaking_by_date[date]) / len(speaking_by_date[date]), 1))
            else:
                chart_data['speaking_scores'].append(0)  # Use 0 instead of None for better chart display
            
            # Writing: average if multiple submissions on same date
            if date in writing_by_date:
                chart_data['writing_scores'].append(round(sum(writing_by_date[date]) / len(writing_by_date[date]), 1))
            else:
                chart_data['writing_scores'].append(0)  # Use 0 instead of None
            
            # Handwritten: average if multiple submissions on same date
            if date in handwritten_by_date:
                chart_data['handwritten_scores'].append(round(sum(handwritten_by_date[date]) / len(handwritten_by_date[date]), 1))
            else:
                chart_data['handwritten_scores'].append(0)  # Use 0 instead of None
            
            # Quiz: average if multiple quizzes on same date
            if date in quiz_by_date:
                chart_data['quiz_scores'].append(round(sum(quiz_by_date[date]) / len(quiz_by_date[date]), 1))
            else:
                chart_data['quiz_scores'].append(0)  # Use 0 instead of None
        
        # Calculate Handwritten Score for insights
        handwritten_score = 0.0
        if handwritten_subs:
            handwritten_score = round(sum(s.grade.score for s in handwritten_subs) / len(handwritten_subs), 1)
        
        # Calculate Quiz Score for insights
        quiz_score = 0.0
        if all_quizzes:
            quiz_scores_list = [q.score for q in all_quizzes if q.score is not None]
            quiz_score = round(sum(quiz_scores_list) / len(quiz_scores_list), 1) if quiz_scores_list else 0.0
        
        # Determine AI Performance Insights (Strongest and Weakest areas)
        area_scores = {
            'Speaking': speaking_score,
            'Writing': writing_score,
            'Quiz': quiz_score,
            'Handwritten': handwritten_score
        }
        
        # Filter out zero scores for comparison
        non_zero_scores = {k: v for k, v in area_scores.items() if v > 0}
        
        if non_zero_scores:
            strongest_area = max(non_zero_scores, key=non_zero_scores.get)
            weakest_area = min(non_zero_scores, key=non_zero_scores.get)
            strongest_score = non_zero_scores[strongest_area]
            weakest_score = non_zero_scores[weakest_area]
        else:
            # If all scores are zero, show default values
            strongest_area = 'Speaking'
            weakest_area = 'Handwritten'
            strongest_score = 0.0
            weakest_score = 0.0
        
        # Determine Recommended Next Step
        recommended_next = "Start Your First Activity"
        recommended_link = "/assignments"
        if not speaking_subs:
            recommended_next = "Improve Your Speaking"
            recommended_link = "/speaking"
        elif not writing_subs:
            recommended_next = "Improve Your Writing"
            recommended_link = "/submit/writing"
        elif speaking_score < 70:
            recommended_next = "Improve Your Speaking"
            recommended_link = "/speaking"
        elif writing_score < 70:
            recommended_next = "Improve Your Writing"
            recommended_link = "/submit/writing"
        elif completed_quizzes == 0:
            recommended_next = "Take a Quiz"
            recommended_link = "/quizzes"
        
        # Get latest graded submission for recommendations
        latest_graded = Submission.query.filter_by(student_id=current_user.id).join(Grade).order_by(Submission.created_at.desc()).first()
        
        # Get recommendations using StatsService
        recommendations = StatsService.fetch_recommendations(current_user.id)
        
        # Get user goals using GoalService
        user_goals = GoalService.get_user_goals(current_user.id)[:2]
        
        # Calculate pending tasks (all activities - in a real app, these would be filtered by student assignments)
        # For now, we'll count activities with future due dates
        pending_activities = LearningActivity.query.filter(
            LearningActivity.due_date >= datetime.utcnow()
        ).order_by(LearningActivity.due_date.asc()).all()
        pending_count = len(pending_activities)
        
        # Calculate total submissions
        total_submissions = len(submissions)
        
        # Calculate average score across all graded submissions
        graded_subs = [s for s in submissions if s.grade]
        avg_score = round(sum(s.grade.score for s in graded_subs) / len(graded_subs), 1) if graded_subs else 0.0
        
        return render_template('dashboard.html', 
                               submissions=submissions,
                               recent_submissions=recent_submissions,
                               speaking_score=speaking_score,
                               writing_score=writing_score,
                               quiz_progress=quiz_progress,
                               current_streak=current_streak,
                               weekly_goal_current=weekly_goal_current,
                               weekly_goal_target=weekly_goal_target,
                               weekly_goal_percentage=weekly_goal_percentage,
                               weekly_goal_remaining=weekly_goal_remaining,
                               recommended_next=recommended_next,
                               recommended_link=recommended_link,
                               latest_graded=latest_graded,
                               goals=user_goals,
                               speaking_subs=speaking_subs,
                               writing_subs=writing_subs,
                               has_chart_data=len(recent_submissions) > 0,
                               chart_data=chart_data,
                               pending_count=pending_count,
                               total_submissions=total_submissions,
                               average_score=avg_score,
                               strongest_area=strongest_area,
                               strongest_score=strongest_score,
                               weakest_area=weakest_area,
                               weakest_score=weakest_score,
                               recommendations=recommendations)

    @app.route('/assignments')
    @login_required
    def view_assignments():
        activities = LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
        now = datetime.utcnow()
        
        # Calculate status counts
        all_count = len(activities)
        pending_count = len([a for a in activities if a.due_date and a.due_date >= now])
        completed_count = len([a for a in activities if a.due_date and a.due_date < now])
        
        return render_template('assignments.html', 
                               activities=activities,
                               all_count=all_count,
                               pending_count=pending_count,
                               completed_count=completed_count,
                               now=now)

    @app.route('/instructor/assignments')
    @role_required('Instructor')
    def instructor_assignments():
        activities = LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
        now = datetime.utcnow()
        return render_template('instructor_assignments.html', activities=activities, now=now)

    @app.route('/instructor/assignments/create', methods=['GET', 'POST'])
    @role_required('Instructor')
    def instructor_create_assignment():
        if request.method == 'POST':
            title = request.form.get('title')
            activity_type = request.form.get('activity_type')
            due_date_str = request.form.get('due_date')
            description = request.form.get('description')

            if not title or not activity_type:
                flash('Title and type are required.', 'danger')
                return redirect(url_for('instructor_create_assignment'))

            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('instructor_create_assignment'))

            new_activity = LearningActivity(
                instructor_id=current_user.id,
                title=title,
                activity_type=activity_type,
                description=description,
                due_date=due_date
            )
            db.session.add(new_activity)
            db.session.commit()
            flash('Assignment created.', 'success')
            return redirect(url_for('instructor_assignments'))

        return render_template('instructor_assignment_create.html')

    @app.route('/speaking')
    @login_required
    def speaking():
        # Get speaking submissions
        submissions = Submission.query.filter_by(student_id=current_user.id, submission_type='SPEAKING').all()
        speaking_subs = [s for s in submissions if s.grade]
        
        # Calculate average score
        avg_score = 0.0
        if speaking_subs:
            scores = []
            for sub in speaking_subs:
                if sub.grade.pronunciation_score and sub.grade.fluency_score:
                    scores.append((sub.grade.pronunciation_score + sub.grade.fluency_score) / 2)
            avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        
        # Get last practice date
        last_practice = None
        if speaking_subs:
            last_sub = max(speaking_subs, key=lambda x: x.created_at)
            last_practice = last_sub.created_at.strftime('%b %d') if last_sub.created_at else None
        
        total_recordings = len(speaking_subs)
        
        return render_template('speaking.html', 
                               avg_score=avg_score,
                               last_practice=last_practice,
                               total_recordings=total_recordings,
                               analysis_results=None)

    @app.route('/instructor/library')
    @role_required('Instructor')
    def instructor_library():
        activities = LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
        return render_template('instructor_library.html', activities=activities)

    @app.route('/quizzes')
    @login_required
    def quizzes():
        # Get quizzes using QuizRepository
        user_quizzes = QuizRepository.get_quizzes(user_id=current_user.id)
        # Get available questions for new quizzes
        available_questions = Question.query.all()
        return render_template('quizzes.html', quizzes=user_quizzes, available_questions=available_questions)

    @app.route('/quiz/start', methods=['GET', 'POST'])
    @login_required
    def start_quiz():
        if request.method == 'POST':
            # Get questions using QuizService
            questions = QuizService.get_questions(limit=5)
            
            if not questions:
                flash("No questions available. Please contact your instructor.", "danger")
                return redirect(url_for('quizzes'))
            
            # Store questions in session for quiz flow
            from flask import session
            session['quiz_questions'] = [q.id for q in questions]
            session['quiz_answers'] = {}
            session['quiz_current'] = 0
            session['quiz_started'] = True
            
            return redirect(url_for('quiz_question'))
        
        return redirect(url_for('quizzes'))

    @app.route('/quiz/question', methods=['GET', 'POST'])
    @login_required
    def quiz_question():
        from flask import session
        
        if not session.get('quiz_started'):
            flash("Please start a quiz first.", "danger")
            return redirect(url_for('quizzes'))
        
        question_ids = session.get('quiz_questions', [])
        current_idx = session.get('quiz_current', 0)
        answers = session.get('quiz_answers', {})
        
        if request.method == 'POST':
            # Check if this is an AJAX request for instant feedback
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                question_id = request.json.get('question_id', type=int)
                answer = request.json.get('answer', '')
                
                if question_id:
                    is_correct = QuizService.check_answer(question_id, answer)
                    question = Question.query.get(question_id)
                    return jsonify({
                        'correct': is_correct,
                        'correct_answer': question.correct_answer if question else None
                    })
            
            # Regular form submission - save answer and move to next
            question_id = request.form.get('question_id', type=int)
            answer = request.form.get('answer', '')
            
            if question_id:
                answers[question_id] = answer
                session['quiz_answers'] = answers
            
            # Move to next question
            current_idx += 1
            session['quiz_current'] = current_idx
            
            if current_idx >= len(question_ids):
                return redirect(url_for('finish_quiz'))
        
        # Get current question
        if current_idx >= len(question_ids):
            return redirect(url_for('finish_quiz'))
        
        question = Question.query.get(question_ids[current_idx])
        if not question:
            flash("Question not found.", "danger")
            return redirect(url_for('quizzes'))
        
        is_last = (current_idx == len(question_ids) - 1)
        previous_answer = answers.get(question.id) if question.id in answers else None
        
        return render_template('quiz_question.html', question=question, 
                             current=current_idx + 1, total=len(question_ids),
                             is_last=is_last, previous_answer=previous_answer)

    @app.route('/quiz/finish', methods=['GET', 'POST'])
    @login_required
    def finish_quiz():
        from flask import session
        
        if not session.get('quiz_started'):
            flash("Please start a quiz first.", "danger")
            return redirect(url_for('quizzes'))
        
        question_ids = session.get('quiz_questions', [])
        answers = session.get('quiz_answers', {})
        
        # Calculate score using QuizService
        correct, total, score = QuizService.calculate_final_score(question_ids, answers)
        
        # Save quiz result using QuizService
        QuizService.save_result(current_user.id, "Grammar Quiz", score)
        
        # Clear session
        session.pop('quiz_started', None)
        session.pop('quiz_questions', None)
        session.pop('quiz_answers', None)
        session.pop('quiz_current', None)
        
        return render_template('quiz_result.html', score=score, correct=correct, total=total)

    @app.route('/goals', methods=['GET', 'POST'])
    @login_required
    def goals():
        if request.method == 'POST':
            # Handle goal creation
            goal_name = request.form.get('goal_name')
            target_value = request.form.get('target_value', type=int)
            current_value = request.form.get('current_value', type=int, default=0)
            category = request.form.get('category', 'General')  # Category for future use
            
            if goal_name and target_value:
                # Use GoalService to create goal
                new_goal = GoalService.set_goal(
                    user_id=current_user.id,
                    goal_name=goal_name,
                    target_value=target_value,
                    current_value=current_value
                )
                
                # Return JSON for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': 'Goal added successfully!'}), 200
                
                flash('Goal added successfully!', 'success')
                return redirect(url_for('goals'))
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Please fill in all required fields.'}), 400
                
                flash('Please fill in all required fields.', 'error')
                return redirect(url_for('goals'))
        
        # GET request - display goals using GoalService
        user_goals = GoalService.get_user_goals(current_user.id)
        return render_template('goals.html', goals=user_goals)

    @app.route('/delete-goal/<int:goal_id>', methods=['POST'])
    @login_required
    def delete_goal(goal_id):
        goal = GoalRepository.get_goal_by_id(goal_id)
        
        if not goal:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Goal not found'}), 404
            flash('Goal not found.', 'error')
            return redirect(url_for('goals'))
        
        # Ensure user can only delete their own goals
        if goal.user_id != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Permission denied'}), 403
            flash('You do not have permission to delete this goal.', 'error')
            return redirect(url_for('goals'))
        
        try:
            # Use GoalService to delete goal
            success = GoalService.delete_goal(goal_id)
            
            if success:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': 'Goal deleted successfully!'}), 200
                flash('Goal deleted successfully!', 'success')
                return redirect(url_for('goals'))
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Failed to delete goal'}), 500
                flash('An error occurred while deleting the goal.', 'error')
                return redirect(url_for('goals'))
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)}), 500
            flash('An error occurred while deleting the goal.', 'error')
            return redirect(url_for('goals'))
    
    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html')
    
    @app.route('/settings', methods=['GET'])
    @login_required
    def settings():
        # All updates are handled by dedicated endpoints below; this route only renders the page.
        return render_template('settings.html')

    # --- PROFILE & SETTINGS AUXILIARY ROUTES ---

    @app.route('/upload_profile_picture', methods=['POST'])
    @login_required
    def upload_profile_picture():
        from flask import jsonify
        file = request.files.get('profile_image')
        if not file or file.filename == '':
            return jsonify({'success': False, 'message': 'No file provided.'}), 400

        # Ensure profile pictures folder exists
        profile_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/profile_pics')
        os.makedirs(profile_folder, exist_ok=True)

        filename = secure_filename(file.filename)
        save_path = os.path.join(profile_folder, filename)
        file.save(save_path)

        current_user.profile_image = filename
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/update_bio', methods=['POST'])
    @login_required
    def update_bio():
        new_bio = request.form.get('new_bio', '').strip()
        current_user.bio = new_bio or None
        try:
            db.session.commit()
            flash("Bio updated successfully.", "success")
        except Exception:
            db.session.rollback()
            flash("Error updating bio.", "danger")
        return redirect(url_for('profile'))

    @app.route('/update_personal_info', methods=['POST'])
    @login_required
    def update_personal_info():
        current_user.university = request.form.get('university') or None
        current_user.grade = request.form.get('grade') or None
        current_user.teacher = request.form.get('teacher') or None
        current_user.phone = request.form.get('phone') or None
        try:
            db.session.commit()
            flash("Personal information updated successfully.", "success")
        except Exception:
            db.session.rollback()
            flash("Error updating personal information.", "danger")
        return redirect(url_for('profile'))

    @app.route('/change_password', methods=['POST'])
    @login_required
    def change_password():
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for('settings'))

        if not new_password or new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for('settings'))

        current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        try:
            db.session.commit()
            flash("Password changed successfully.", "success")
        except Exception:
            db.session.rollback()
            flash("Error changing password.", "danger")
        return redirect(url_for('settings'))

    @app.route('/update_ai_settings', methods=['POST'])
    @login_required
    def update_ai_settings():
        ai_tone = request.form.get('ai_tone') or 'balanced'
        ai_speed = request.form.get('ai_speed') or '1.0'
        weekly_report = request.form.get('weekly_report') is not None

        current_user.ai_tone = ai_tone
        try:
            current_user.ai_speed = float(ai_speed)
        except ValueError:
            current_user.ai_speed = 1.0
        current_user.weekly_report = weekly_report

        try:
            db.session.commit()
            flash("AI preferences saved.", "success")
        except Exception:
            db.session.rollback()
            flash("Error saving AI preferences.", "danger")
        return redirect(url_for('settings'))
    @app.route('/export')
    @login_required
    def export_data():
        format_type = request.args.get('format', 'csv')
        student_id = current_user.id if current_user.role == 'Student' else None
        
        # Use ReportService to generate report
        report_data = ReportService.export_report(student_id=student_id, format=format_type)
        
        if report_data and format_type == 'csv':
            response = make_response(report_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=report_{current_user.id}.csv'
            return response
        elif report_data and format_type == 'pdf':
            # PDF implementation would go here
            flash("PDF export is not yet fully implemented.", "info")
            return redirect(url_for('dashboard'))
        else:
            flash("Failed to generate report.", "danger")
            return redirect(url_for('dashboard'))

    # ---  INSTRUCTOR DASHBOARD ---

    @app.route('/instructor/dashboard')
    @role_required('Instructor')
    def instructor_dashboard():
        from datetime import timedelta
        from collections import defaultdict
        
        all_subs = Submission.query.all()
        graded_subs = [s for s in all_subs if s.grade]
        class_avg = round(sum(s.grade.score for s in graded_subs) / len(graded_subs), 1) if graded_subs else 0.0
        active_count = len(set(s.student_id for s in all_subs))
        pending_count = len(all_subs) - len(graded_subs)
        
        # Prepare sparkline data for last 7 days
        today = datetime.utcnow().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]  # Last 7 days including today
        
        # Count submissions per day
        submissions_by_date = defaultdict(int)
        pending_by_date = defaultdict(int)
        avg_score_by_date = defaultdict(list)
        active_students_by_date = defaultdict(set)
        
        for sub in all_subs:
            sub_date = sub.created_at.date()
            if sub_date in last_7_days:
                submissions_by_date[sub_date] += 1
                if not sub.grade:
                    pending_by_date[sub_date] += 1
                if sub.grade:
                    avg_score_by_date[sub_date].append(sub.grade.score)
                active_students_by_date[sub_date].add(sub.student_id)
        
        # Create sparkline data arrays
        sparkline_data = {
            'submissions': [submissions_by_date.get(date, 0) for date in last_7_days],
            'pending': [pending_by_date.get(date, 0) for date in last_7_days],
            'class_avg': [round(sum(avg_score_by_date.get(date, [])) / len(avg_score_by_date.get(date, [])), 1) if avg_score_by_date.get(date, []) else 0.0 for date in last_7_days],
            'active_students': [len(active_students_by_date.get(date, set())) for date in last_7_days]
        }

        return render_template('instructor_dashboard.html', 
                               submissions=all_subs, 
                               class_avg=class_avg, 
                               active_count=active_count,
                               pending_count=pending_count,
                               sparkline_data=sparkline_data)

    @app.route('/instructor/students')
    @role_required('Instructor')
    def instructor_students():
        students = User.query.filter_by(role='Student').all()
        return render_template('instructor_students.html', students=students)

    @app.route('/instructor/students/<int:student_id>')
    @role_required('Instructor')
    def instructor_student_detail(student_id):
        student = User.query.filter_by(id=student_id, role='Student').first_or_404()

        submissions = Submission.query.filter_by(student_id=student.id).order_by(Submission.created_at.desc()).all()
        quizzes = Quiz.query.filter_by(user_id=student.id).order_by(Quiz.id.desc()).all()
        goals = LearningGoal.query.filter_by(user_id=student.id).all()

        graded_subs = [s for s in submissions if s.grade]
        avg_score = round(sum(s.grade.score for s in graded_subs) / len(graded_subs), 1) if graded_subs else 0.0
        total_submissions = len(submissions)
        pending_submissions = len([s for s in submissions if not s.grade])

        return render_template(
            'instructor_student_detail.html',
            student=student,
            submissions=submissions,
            quizzes=quizzes,
            goals=goals,
            avg_score=avg_score,
            total_submissions=total_submissions,
            pending_submissions=pending_submissions
        )

    @app.route('/instructor/analytics')
    @role_required('Instructor')
    def instructor_analytics():
        from datetime import timedelta
        from collections import defaultdict
        
        students = User.query.filter_by(role='Student').all()
        all_subs = Submission.query.all()
        graded_subs = [s for s in all_subs if s.grade]
        
        total_students = len(students)
        total_submissions = len(all_subs)
        avg_score = round(sum(s.grade.score for s in graded_subs) / len(graded_subs), 1) if graded_subs else 0.0
        pending_reviews = len(all_subs) - len(graded_subs)
        
        # Chart data for last 7 days
        today = datetime.utcnow().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        submissions_by_date = defaultdict(int)
        
        for sub in all_subs:
            sub_date = sub.created_at.date()
            if sub_date in last_7_days:
                submissions_by_date[sub_date] += 1
        
        chart_labels = [date.strftime('%b %d') for date in last_7_days]
        submission_data = [submissions_by_date.get(date, 0) for date in last_7_days]
        
        # Top students
        top_students = sorted(students, key=lambda s: len(s.submissions) if s.submissions else 0, reverse=True)[:10]
        
        return render_template('instructor_analytics.html',
                               total_students=total_students,
                               total_submissions=total_submissions,
                               avg_score=avg_score,
                               pending_reviews=pending_reviews,
                               chart_labels=chart_labels,
                               submission_data=submission_data,
                               top_students=top_students)

    @app.route('/instructor/feedback')
    @role_required('Instructor')
    def instructor_feedback():
        student_id = request.args.get('student_id', type=int)
        filter_type = request.args.get('type', default=None, type=str)

        query = Submission.query.order_by(Submission.created_at.desc())

        if student_id:
            query = query.filter_by(student_id=student_id)

        if filter_type:
            # Expecting 'writing', 'speaking', 'handwritten' from UI
            submission_type = filter_type.upper()
            query = query.filter_by(submission_type=submission_type)

        submissions = query.all()

        return render_template(
            'instructor_feedback.html',
            submissions=submissions,
            selected_student_id=student_id,
            selected_type=filter_type or 'all'
        )

    @app.route('/instructor/submissions')
    @role_required('Instructor')
    def instructor_submissions():
        submissions = Submission.query.order_by(Submission.created_at.desc()).all()
        return render_template(
            'instructor_feedback.html',
            submissions=submissions,
            selected_student_id=None,
            selected_type='all'
        )

    @app.route('/instructor/pending')
    @role_required('Instructor')
    def instructor_pending():
        submissions = Submission.query.filter(~Submission.grade.has()).order_by(Submission.created_at.desc()).all()
        return render_template(
            'instructor_feedback.html',
            submissions=submissions,
            selected_student_id=None,
            selected_type='all'
        )

    @app.route('/instructor/questions', methods=['GET', 'POST'])
    @role_required('Instructor')
    def manage_questions():
        if request.method == 'POST':
            question_text = request.form.get('question_text')
            option_a = request.form.get('option_a')
            option_b = request.form.get('option_b')
            option_c = request.form.get('option_c', '')
            option_d = request.form.get('option_d', '')
            correct_answer = request.form.get('correct_answer')
            category = request.form.get('category', 'grammar')
            
            if question_text and option_a and option_b and correct_answer:
                new_question = Question(
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c if option_c else None,
                    option_d=option_d if option_d else None,
                    correct_answer=correct_answer.upper(),
                    category=category
                )
                db.session.add(new_question)
                db.session.commit()
                flash("Question added successfully!", "success")
                return redirect(url_for('manage_questions'))
            else:
                flash("Please fill in all required fields.", "danger")
        
        questions = Question.query.all()
        return render_template('manage_questions.html', questions=questions)

    # --- SUBMISSION ROUTES ---

    @app.route('/submit/writing', methods=['GET', 'POST'])
    @role_required('Student')
    def submit_writing():
        activity_id = request.args.get('activity_id')
        if request.method == 'POST':
            text_content = request.form.get('text_content', '').strip()
            file = request.files.get('file')
            
            # Handle file upload using SubmissionService
            if file and file.filename != '':
                # Validate file format
                if not SubmissionService.validate_file_format(file.filename):
                    flash("Invalid file format. Please upload .docx, .pdf, .txt, or image files.", "danger")
                    return redirect(url_for('submit_writing'))
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                if filename.endswith('.docx'):
                    doc = docx.Document(file_path)
                    text_content = "\n".join([p.text for p in doc.paragraphs])
                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f: 
                            text_content = f.read()
                    except:
                        with open(file_path, 'r', encoding='latin-1') as f: 
                            text_content = f.read()
            
            # Check if we have text content
            if not text_content:
                flash("Please provide some text to analyze.", "danger")
                return redirect(url_for('submit_writing'))
            
            # Create submission using SubmissionService
            new_sub = SubmissionService.save_submission_text(
                student_id=current_user.id,
                activity_id=activity_id,
                submission_type='WRITING',
                text_content=text_content,
                file_path=file.filename if file else None
            )

            # Analyze with AI
            print(f"Starting AI analysis for submission {new_sub.id}")
            ai_res = AIService.evaluate_writing(text_content)
            
            # Process evaluation using GradingService
            if ai_res and ai_res.get('score') is not None:
                success = GradingService.process_evaluation(new_sub.id, ai_res)
                if success:
                    NotificationService.notify_grade_ready(current_user.id, new_sub.id)
                    flash("Submission analyzed successfully!", "success")
                else:
                    flash("Failed to save grade.", "danger")
            else:
                error_msg = ai_res.get('general_feedback', 'Unknown error') if ai_res else 'No response from AI'
                flash(f"Analysis failed: {error_msg}", "danger")
            
            return redirect(url_for('dashboard'))
        return render_template('submit_writing.html')

    @app.route('/submit/handwritten', methods=['GET', 'POST'])
    @role_required('Student')
    def submit_handwritten():
        activity_id = request.args.get('activity_id')
        image_path = None
        extracted_text = None
        
        if request.method == 'POST':
            file = request.files.get('file')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                extracted_text = OCRService.extract_text_from_image(file_path)
                if not extracted_text:
                    flash("Failed to extract text from image. Please upload a clearer image with better handwriting.", "danger")
                    return render_template('submit_handwritten.html', 
                                         image_path=None,
                                         extracted_text=None)
                
                if extracted_text:
                    # Save submission using SubmissionService
                    new_sub = SubmissionService.save_submission_text(
                        student_id=current_user.id,
                        activity_id=activity_id,
                        submission_type='HANDWRITTEN',
                        text_content=extracted_text,
                        file_path=filename
                    )
                    
                    ai_res = AIService.evaluate_writing(extracted_text)
                    if ai_res:
                        # Process evaluation using GradingService
                        success = GradingService.process_evaluation(new_sub.id, ai_res)
                        if success:
                            NotificationService.notify_grade_ready(current_user.id, new_sub.id)
                    
                    # Set image path for display (relative to static folder)
                    image_path = f"uploads/{filename}"
                    flash("Image processed successfully!", "success")
                    
        return render_template('submit_handwritten.html', 
                               image_path=image_path,
                               extracted_text=extracted_text)

    @app.route('/history')
    @login_required
    def history():
        filter_type = request.args.get('filter')
        query = Submission.query.filter_by(student_id=current_user.id)
        
        # Apply filter if specified
        if filter_type:
            if filter_type == 'speaking':
                query = query.filter_by(submission_type='SPEAKING')
            elif filter_type == 'writing':
                query = query.filter_by(submission_type='WRITING')
            elif filter_type == 'handwritten':
                query = query.filter_by(submission_type='HANDWRITTEN')
            elif filter_type == 'quiz':
                query = query.filter_by(submission_type='QUIZ')
        
        submissions = query.order_by(Submission.created_at.desc()).all()
        return render_template('history.html', submissions=submissions)

    @app.route('/feedback/<int:submission_id>')
    @login_required
    def view_feedback(submission_id):
        # Use FeedbackRepository to find feedback
        grade = FeedbackRepository.find_feedback_by_submission_id(submission_id)
        sub = Submission.query.get_or_404(submission_id)
        
        # Ensure user can only view their own submissions (unless instructor)
        if current_user.role != 'Instructor' and sub.student_id != current_user.id:
            flash("You don't have permission to view this report.", "error")
            return redirect(url_for('dashboard'))
        return render_template('feedback.html', submission=sub)

    @app.route('/adjust_grade/<int:submission_id>', methods=['GET', 'POST'])
    @role_required('Instructor')
    def adjust_grade(submission_id):
        submission = Submission.query.get_or_404(submission_id)
        
        if not submission.grade:
            flash("No grade found for this submission.", "danger")
            return redirect(url_for('instructor_dashboard'))
        
        if request.method == 'POST':
            new_score = request.form.get('new_score', type=float)
            new_feedback = request.form.get('new_feedback', '')
            
            if new_score is not None and 0 <= new_score <= 100:
                # Use GradingService to update grade
                success = GradingService.update_student_grade(submission.id, new_score, new_feedback)
                if success:
                    NotificationService.notify_grade_ready(submission.student_id, submission.id)
                    flash("Grade adjusted successfully!", "success")
                    return redirect(url_for('instructor_dashboard'))
                else:
                    flash("Failed to update grade.", "danger")
            else:
                flash("Invalid score. Please enter a value between 0 and 100.", "danger")
        
        return render_template('adjust_grade.html', submission=submission)

    @app.route('/delete_submission/<int:submission_id>', methods=['POST'])
    @login_required
    def delete_submission(submission_id):
        from flask import jsonify
        sub = Submission.query.get_or_404(submission_id)
        # Ensure user can only delete their own submissions
        if sub.student_id != current_user.id:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        try:
            # Delete associated grade if exists
            if sub.grade:
                db.session.delete(sub.grade)
            
            # Delete submission
            db.session.delete(sub)
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/privacy')
    def privacy():
        return render_template('privacy.html')

    @app.route('/terms')
    def terms():
        return render_template('terms.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
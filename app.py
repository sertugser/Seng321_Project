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
from models.entities import User, Submission, Grade, LearningActivity, LearningGoal, Quiz, QuizDetail, Question, Course, Enrollment, PlatformSettings, AIIntegration, LMSIntegration
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
from repositories.admin_repository import AdminRepository
from services.admin_service import AdminService

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

    # --- AUTHENTICATION CHECK & CACHE CONTROL ---
    @app.before_request
    def check_user_auth():
        public_routes = ['login', 'register', 'static', 'privacy', 'terms', 'index']
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
        
        # Username kontrolü
        if User.query.filter_by(username=username).first():
            flash("This username is already taken!", "danger")
            return redirect(url_for('login', mode='register'))
        
        # Email kontrolü
        if User.query.filter_by(email=email).first():
            flash("This email address is already in use!", "danger")
            return redirect(url_for('login', mode='register'))
        
        try:
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_pw, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration is successful, you can now log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "danger")
            return redirect(url_for('login', mode='register'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # If already authenticated, redirect to appropriate dashboard
        if current_user.is_authenticated:
            if current_user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif current_user.role == 'Instructor':
                return redirect(url_for('instructor_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        # Clear flash messages on GET request (when coming from logout)
        if request.method == 'GET':
            from flask import session
            session.pop('_flashes', None)
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash("Please enter both email and password.", "danger")
                return render_template('login.html')
            
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                # Redirect based on role
                if user.role == 'Admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'Instructor':
                    return redirect(url_for('instructor_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            flash("Invalid email or password.", "danger")
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        # Clear all flash messages and session data before logout
        from flask import session
        session.clear()  # Clear all session data
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
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
        
        # Get adaptive insights (UC17)
        from services.adaptive_insights_service import AdaptiveInsightsService
        adaptive_insights = AdaptiveInsightsService.get_active_insights(current_user.id)
        
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
                               recommendations=recommendations,
                               adaptive_insights=adaptive_insights)

    @app.route('/assignments')
    @login_required
    def view_assignments():
        all_activities = LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
        now = datetime.utcnow()

        # Student submissions to mark completed assignments (including quiz submissions)
        user_subs = Submission.query.filter_by(student_id=current_user.id).all()
        submitted_ids = set(s.activity_id for s in user_subs if s.activity_id and s.activity_id is not None)
        
        # Get submissions with their grades for status determination
        submissions_with_grades = {s.activity_id: s for s in user_subs if s.activity_id and s.grade}

        # Filter assignments for students
        if current_user.role == 'Student':
            # Get all active assignments (not expired)
            active_activities = [a for a in all_activities if not a.due_date or a.due_date >= now]
            
            # Categorize assignments:
            # Active: not submitted yet
            active_activities_list = [a for a in active_activities if a.id not in submitted_ids]
            
            # Pending: submitted but waiting for instructor approval (has grade but not approved)
            pending_activities = []
            completed_activities = []
            
            for activity_id in submitted_ids:
                activity = next((a for a in all_activities if a.id == activity_id), None)
                if activity:
                    submission = submissions_with_grades.get(activity_id)
                    if submission and submission.grade:
                        if submission.grade.instructor_approved:
                            completed_activities.append(activity)
                        else:
                            pending_activities.append(activity)
                    else:
                        # Submitted but no grade yet - treat as pending
                        pending_activities.append(activity)
            
            # Default: show active
            activities = active_activities_list
        else:
            activities = all_activities
            active_activities_list = activities
            pending_activities = []
            completed_activities = []

        # Calculate counts for display
        active_count = len(active_activities_list)
        pending_count = len(pending_activities)
        completed_count = len(completed_activities)

        return render_template('assignments.html', 
                               activities=activities,
                               active_activities=active_activities_list,
                               pending_activities=pending_activities,
                               completed_activities=completed_activities,
                               active_count=active_count,
                               pending_count=pending_count,
                               completed_count=completed_count,
                               now=now,
                               submitted_ids=submitted_ids,
                               user_subs=user_subs,
                               submissions_with_grades=submissions_with_grades)

    @app.route('/instructor/assignments')
    @role_required('Instructor')
    def instructor_assignments():
        activities = LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
        now = datetime.utcnow()
        
        # Calculate submission stats for each activity
        # Same logic as instructor_assignment_detail
        activity_stats = []
        for activity in activities:
            if not activity or not hasattr(activity, 'id'):
                continue
            submissions = Submission.query.filter_by(activity_id=activity.id).all()
            total_submissions = len(submissions)
            # Graded = instructor approved
            graded_submissions = len([s for s in submissions if s.grade and s.grade.instructor_approved])
            # Pending = has AI grade but not approved yet
            pending_submissions = len([s for s in submissions if s.grade and not s.grade.instructor_approved])
            
            activity_stats.append({
                'activity': activity,
                'total_submissions': total_submissions,
                'graded_submissions': graded_submissions,
                'pending_submissions': pending_submissions
            })
        
        return render_template('instructor_assignments.html', 
                             activity_stats=activity_stats, 
                             now=now)

    @app.route('/instructor/assignments/create', methods=['GET', 'POST'])
    @role_required('Instructor')
    def instructor_create_assignment():
        if request.method == 'POST':
            title = request.form.get('title')
            activity_type = request.form.get('activity_type')
            due_date_str = request.form.get('due_date')
            description = request.form.get('description')
            quiz_category = request.form.get('quiz_category') if activity_type == 'QUIZ' else None

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
                quiz_category=quiz_category,
                due_date=due_date
            )
            db.session.add(new_activity)
            db.session.commit()
            flash('Assignment created.', 'success')
            return redirect(url_for('instructor_assignments'))

        return render_template('instructor_assignment_create.html')

    @app.route('/speaking', methods=['GET', 'POST'])
    @role_required('Student')
    def speaking():
        activity_id = request.args.get('activity_id')
        
        if request.method == 'POST':
            audio_file = request.files.get('audio_file')
            
            if not audio_file or audio_file.filename == '':
                flash("Please record or upload an audio file.", "danger")
                return redirect(url_for('speaking'))
            
            # Validate file format
            if not SubmissionService.validate_file_format(audio_file.filename, 'SPEAKING'):
                flash("Invalid audio format. Please upload MP3 or WAV files.", "danger")
                return redirect(url_for('speaking'))
            
            # Check file size (max 10MB)
            audio_file.seek(0, os.SEEK_END)
            file_size = audio_file.tell()
            audio_file.seek(0)
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                flash("File size exceeds 10MB limit.", "danger")
                return redirect(url_for('speaking'))
            
            # Save audio file
            filename = secure_filename(audio_file.filename)
            # Add timestamp to avoid conflicts
            from datetime import datetime
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            audio_file.save(file_path)
            
            # Check if already submitted for this activity
            if activity_id:
                existing = Submission.query.filter_by(
                    student_id=current_user.id,
                    activity_id=activity_id
                ).first()
                if existing:
                    flash("You have already submitted this assignment.", "danger")
                    return redirect(url_for('speaking'))
                
                # Check due date
                activity = LearningActivity.query.get(activity_id)
                if activity and activity.due_date:
                    if datetime.utcnow() > activity.due_date:
                        flash("This assignment has expired. The due date has passed.", "danger")
                        return redirect(url_for('speaking'))
            
            # Create submission
            new_sub, error_msg = SubmissionService.save_submission_text(
                student_id=current_user.id,
                activity_id=activity_id,
                submission_type='SPEAKING',
                text_content=None,
                file_path=filename
            )
            
            if not new_sub:
                flash(error_msg or "Failed to create submission.", "danger")
                return redirect(url_for('speaking'))
            
            # Analyze with AI
            print(f"Starting AI analysis for speaking submission {new_sub.id}")
            ai_res = AIService.evaluate_speaking(file_path)
            
            # Process evaluation using GradingService
            if ai_res and ai_res.get('pronunciation_score') is not None:
                success = GradingService.process_speaking_evaluation(new_sub.id, ai_res)
                if success:
                    NotificationService.notify_grade_ready(current_user.id, new_sub.id)
                    flash("Speaking analyzed successfully!", "success")
                    # Redirect to show results
                    return redirect(url_for('speaking', submission_id=new_sub.id))
                else:
                    flash("Failed to save grade.", "danger")
            else:
                error_msg = ai_res.get('feedback', 'Unknown error') if ai_res else 'No response from AI'
                flash(f"Analysis failed: {error_msg}", "danger")
            
            return redirect(url_for('speaking'))
        
        # GET request - display page
        submission_id = request.args.get('submission_id', type=int)
        analysis_results = None
        
        # If viewing a specific submission, get its results
        if submission_id:
            submission = Submission.query.filter_by(id=submission_id, student_id=current_user.id).first()
            if submission and submission.grade:
                # Get tips from general_feedback or generate based on scores
                tips = []
                if submission.grade.pronunciation_score and submission.grade.pronunciation_score < 80:
                    tips.append("Practice difficult words slowly, then gradually increase speed")
                    tips.append("Record yourself and compare with native speakers")
                if submission.grade.fluency_score and submission.grade.fluency_score < 80:
                    tips.append("Read aloud daily to improve speech flow")
                    tips.append("Practice speaking without long pauses")
                if not tips:
                    tips.append("Keep up the excellent work!")
                    tips.append("Continue practicing to maintain your level")
                
                analysis_results = {
                    'pronunciation_score': submission.grade.pronunciation_score,
                    'fluency_score': submission.grade.fluency_score,
                    'feedback': submission.grade.general_feedback,
                    'tips': tips
                }
        
        # Get speaking submissions for stats
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
                               analysis_results=analysis_results)

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
        activity_id = request.args.get('activity_id', type=int)
        category = None
        
        # If started from assignment, get category from activity
        if activity_id:
            activity = LearningActivity.query.get(activity_id)
            if activity and activity.activity_type == 'QUIZ':
                category = activity.quiz_category
        
        if request.method == 'POST' or activity_id:
            # Get questions using QuizService with optional category
            questions = QuizService.get_questions(limit=5, category=category)
            
            if not questions:
                flash("No questions available for this category.", "danger")
                return redirect(url_for('quizzes'))
            
            # Store questions in session for quiz flow
            from flask import session
            session['quiz_questions'] = [q.id for q in questions]
            session['quiz_answers'] = {}
            session['quiz_current'] = 0
            session['quiz_started'] = True
            if activity_id:
                session['quiz_activity_id'] = activity_id
            
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
        # answers stored with string keys in session
        answers = session.get('quiz_answers', {})
        
        if request.method == 'POST':
            question_id = request.form.get('question_id', type=int)
            answer = request.form.get('answer', '')
            
            if question_id:
                answers[str(question_id)] = answer
                session['quiz_answers'] = dict(answers)
            
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

        # Build per-question details for result page
        details = []
        for q_id in question_ids:
            question = Question.query.get(q_id)
            user_answer = answers.get(str(q_id))
            correct_answer = question.correct_answer if question else None
            is_correct = user_answer and question and user_answer.upper() == correct_answer.upper()
            details.append({
                'question_text': question.question_text if question else '',
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
            })
        
        # Save quiz result and detailed answers using QuizService
        quiz_title = "Grammar Quiz"
        
        # Check if this was an assignment submission
        activity_id = session.get('quiz_activity_id')
        if activity_id:
            activity = LearningActivity.query.get(activity_id)
            if activity:
                quiz_title = activity.title
                
                # Create Submission
                new_sub = Submission(
                    student_id=current_user.id,
                    activity_id=activity.id,
                    submission_type='QUIZ',
                    text_content=f"Quiz completed: {activity.title} (Score: {score}%)"
                )
                db.session.add(new_sub)
                db.session.flush() # get id
                
                # Create Grade
                # Quiz grades are auto-approved since they're automatically graded
                new_grade = Grade(
                    submission_id=new_sub.id,
                    score=score,
                    general_feedback=f"Auto-graded quiz. Correct: {correct}/{total}",
                    instructor_approved=True  # Auto-approved for quizzes
                )
                db.session.add(new_grade)
                db.session.commit() # Commit submission and grade
                flash("Assignment marked as completed!", "success")
        
        QuizService.save_result(current_user.id, quiz_title, score, details=details)
        
        # Clear session
        session.pop('quiz_started', None)
        session.pop('quiz_questions', None)
        session.pop('quiz_answers', None)
        session.pop('quiz_current', None)
        session.pop('quiz_activity_id', None)
        
        return render_template('quiz_result.html', score=score, correct=correct, total=total, details=details, is_review=False)

    @app.route('/quiz/review/<int:quiz_id>')
    @login_required
    def quiz_review(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)

        # Permission: student can only see own quiz, instructor can see all
        if current_user.role != 'Instructor' and quiz.user_id != current_user.id:
            flash("You don't have permission to view this quiz.", "danger")
            return redirect(url_for('dashboard'))

        details_rows = QuizDetail.query.filter_by(quiz_id=quiz.id).all()

        # Fallback: if no stored details, just show simple result
        details = []
        correct = 0
        total = 0
        if details_rows:
            for d in details_rows:
                details.append({
                    'question_text': d.question_text,
                    'user_answer': d.user_answer,
                    'correct_answer': d.correct_answer,
                    'is_correct': d.is_correct,
                })
                total += 1
                if d.is_correct:
                    correct += 1

        return render_template(
            'quiz_result.html',
            score=quiz.score,
            correct=correct,
            total=total,
            details=details,
            is_review=True
        )

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
                category = request.form.get('category', 'General')
                # Use GoalService to create goal
                new_goal = GoalService.set_goal(
                    user_id=current_user.id,
                    goal_name=goal_name,
                    target_value=target_value,
                    current_value=current_value,
                    category=category
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
    
    @app.route('/goals/<int:goal_id>', methods=['GET', 'PUT'])
    @login_required
    def get_or_update_goal(goal_id):
        goal = GoalRepository.get_goal_by_id(goal_id)
        
        if not goal:
            return jsonify({'success': False, 'message': 'Goal not found'}), 404
        
        # Ensure user can only access their own goals
        if goal.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        if request.method == 'GET':
            # Return goal data
            return jsonify({
                'success': True,
                'goal': {
                    'id': goal.id,
                    'goal_name': goal.goal_name,
                    'category': goal.category or 'General',
                    'target_value': goal.target_value,
                    'current_value': goal.current_value
                }
            })
        
        elif request.method == 'PUT':
            # Update goal
            goal_name = request.form.get('goal_name')
            target_value = request.form.get('target_value', type=int)
            current_value = request.form.get('current_value', type=int)
            category = request.form.get('category', 'General')
            
            updated_goal = GoalService.update_goal(
                goal_id=goal_id,
                goal_name=goal_name,
                target_value=target_value,
                current_value=current_value,
                category=category
            )
            
            if updated_goal:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': 'Goal updated successfully!'}), 200
                flash('Goal updated successfully!', 'success')
                return redirect(url_for('goals'))
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Failed to update goal'}), 500
                flash('Failed to update goal.', 'error')
                return redirect(url_for('goals'))

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
    
    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if username:
                current_user.username = username
            if email:
                existing = User.query.filter_by(email=email).first()
                if existing and existing.id != current_user.id:
                    flash("Email already exists!", "danger")
                    return redirect(url_for('settings'))
                current_user.email = email
            if password:
                current_user.password = generate_password_hash(password, method='pbkdf2:sha256')
            
            try:
                db.session.commit()
                flash("Settings updated successfully!", "success")
            except:
                db.session.rollback()
                flash("Error updating settings.", "danger")
            
            return redirect(url_for('settings'))
        
        return render_template('settings.html')
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
            response = make_response(report_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=report_{current_user.id}_{datetime.utcnow().strftime("%Y%m%d")}.pdf'
            return response
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
        all_quizzes = Quiz.query.all()
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
                               quizzes=all_quizzes,
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
        # Show submissions with AI grades that need instructor approval (instructor_approved=False)
        from models.entities import Grade
        submissions = Submission.query.join(Grade).filter(
            Grade.instructor_approved == False
        ).order_by(Submission.created_at.desc()).all()
        return render_template(
            'instructor_feedback.html',
            submissions=submissions,
            selected_student_id=None,
            selected_type='all'
        )
    
    @app.route('/instructor/assignments/<int:activity_id>')
    @role_required('Instructor')
    def instructor_assignment_detail(activity_id):
        activity = LearningActivity.query.get_or_404(activity_id)
        submissions = Submission.query.filter_by(activity_id=activity_id).order_by(Submission.created_at.desc()).all()
        
        total_submissions = len(submissions)
        # Graded = instructor approved
        graded_submissions = len([s for s in submissions if s.grade and s.grade.instructor_approved])
        # Pending = has AI grade but not approved yet
        pending_submissions = len([s for s in submissions if s.grade and not s.grade.instructor_approved])
        
        # Get students who submitted
        student_ids = set(s.student_id for s in submissions)
        students = User.query.filter(User.id.in_(student_ids)).all() if student_ids else []
        
        return render_template('instructor_assignment_detail.html',
                             activity=activity,
                             submissions=submissions,
                             total_submissions=total_submissions,
                             graded_submissions=graded_submissions,
                             pending_submissions=pending_submissions,
                             students=students)
    
    @app.route('/instructor/assignments/<int:activity_id>/edit', methods=['GET', 'POST'])
    @role_required('Instructor')
    def instructor_edit_assignment(activity_id):
        activity = LearningActivity.query.get_or_404(activity_id)
        
        if activity.instructor_id != current_user.id:
            flash("You don't have permission to edit this assignment.", "danger")
            return redirect(url_for('instructor_assignments'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            activity_type = request.form.get('activity_type')
            due_date_str = request.form.get('due_date')
            description = request.form.get('description')
            quiz_category = request.form.get('quiz_category') if activity_type == 'QUIZ' else None
            
            if not title or not activity_type:
                flash('Title and type are required.', 'danger')
                return redirect(url_for('instructor_edit_assignment', activity_id=activity_id))
            
            activity.title = title
            activity.activity_type = activity_type
            activity.description = description
            activity.quiz_category = quiz_category
            
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('instructor_edit_assignment', activity_id=activity_id))
            activity.due_date = due_date
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('instructor_assignment_detail', activity_id=activity_id))
        
        return render_template('instructor_assignment_edit.html', activity=activity)
    
    @app.route('/instructor/assignments/<int:activity_id>/delete', methods=['POST'])
    @role_required('Instructor')
    def instructor_delete_assignment(activity_id):
        activity = LearningActivity.query.get_or_404(activity_id)
        
        if activity.instructor_id != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Permission denied'}), 403
            flash("You don't have permission to delete this assignment.", "danger")
            return redirect(url_for('instructor_assignments'))
        
        # Delete associated submissions and grades
        submissions = Submission.query.filter_by(activity_id=activity_id).all()
        for submission in submissions:
            if submission.grade:
                db.session.delete(submission.grade)
            db.session.delete(submission)
        
        db.session.delete(activity)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Assignment deleted successfully!'}), 200
        
        flash('Assignment deleted successfully!', 'success')
        return redirect(url_for('instructor_assignments'))
    
    @app.route('/instructor/submissions/<int:submission_id>/approve', methods=['POST'])
    @role_required('Instructor')
    def approve_submission(submission_id):
        submission = Submission.query.get_or_404(submission_id)
        
        if not submission.grade:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'No grade found for this submission'}), 400
            flash('No grade found for this submission.', 'danger')
            return redirect(url_for('instructor_pending'))
        
        success = GradingService.approve_grade(submission_id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if success:
                return jsonify({'success': True, 'message': 'Grade approved successfully!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Failed to approve grade'}), 400
        
        if success:
            flash('Grade approved successfully!', 'success')
        else:
            flash('Failed to approve grade.', 'danger')
        
        return redirect(url_for('instructor_pending'))

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
            new_sub, error_msg = SubmissionService.save_submission_text(
                student_id=current_user.id,
                activity_id=activity_id,
                submission_type='WRITING',
                text_content=text_content,
                file_path=file.filename if file else None
            )

            if not new_sub:
                flash(error_msg or "Failed to create submission.", "danger")
                return render_template('submit_writing.html', submitted_text=text_content)

            # Analyze with AI
            print(f"Starting AI analysis for submission {new_sub.id}")
            ai_res = AIService.evaluate_writing(text_content)
            
            # Process evaluation using GradingService
            if ai_res and ai_res.get('score') is not None:
                success = GradingService.process_evaluation(new_sub.id, ai_res)
                if success:
                    NotificationService.notify_grade_ready(current_user.id, new_sub.id)
                    flash("Submission analyzed successfully!", "success")
                    # Reload the submission with grade to show results on the same page
                    new_sub = Submission.query.get(new_sub.id)
                    return render_template('submit_writing.html', 
                                         grade=new_sub.grade,
                                         submitted_text=text_content,
                                         analysis_results=ai_res)
                else:
                    flash("Failed to save grade.", "danger")
            else:
                error_msg = ai_res.get('general_feedback', 'Unknown error') if ai_res else 'No response from AI'
                flash(f"Analysis failed: {error_msg}", "danger")
            
            return render_template('submit_writing.html', submitted_text=text_content)
        
        # GET request - check if there's a submission_id to show results
        submission_id = request.args.get('submission_id', type=int)
        grade = None
        submitted_text = None
        
        if submission_id:
            submission = Submission.query.filter_by(id=submission_id, student_id=current_user.id).first()
            if submission:
                grade = submission.grade
                submitted_text = submission.text_content
        
        return render_template('submit_writing.html', grade=grade, submitted_text=submitted_text)

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
                    new_sub, error_msg = SubmissionService.save_submission_text(
                        student_id=current_user.id,
                        activity_id=activity_id,
                        submission_type='HANDWRITTEN',
                        text_content=extracted_text,
                        file_path=filename
                    )
                    
                    if not new_sub:
                        flash(error_msg or "Failed to create submission.", "danger")
                        return render_template('submit_handwritten.html', 
                                             image_path=None,
                                             extracted_text=None)
                    
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

        # For quiz-only history, use Quiz table
        if filter_type == 'quiz':
            quizzes = QuizRepository.get_quizzes(user_id=current_user.id)
            submissions = []
        else:
            query = Submission.query.filter_by(student_id=current_user.id)
            
            if filter_type:
                if filter_type == 'speaking':
                    query = query.filter_by(submission_type='SPEAKING')
                elif filter_type == 'writing':
                    query = query.filter_by(submission_type='WRITING')
                elif filter_type == 'handwritten':
                    query = query.filter_by(submission_type='HANDWRITTEN')
            
            submissions = query.order_by(Submission.created_at.desc()).all()

            # In "All" view also include quizzes; for filtered speaking/writing/handwritten, hide them
            if not filter_type or filter_type == 'all':
                quizzes = QuizRepository.get_quizzes(user_id=current_user.id)
            else:
                quizzes = []
        
        # For assignments history
        assignments = []
        activity_submissions = {}
        if filter_type == 'assignments':
            # Get all completed assignments (submitted ones)
            user_subs_all = Submission.query.filter_by(student_id=current_user.id).all()
            completed_activity_ids = set(s.activity_id for s in user_subs_all if s.activity_id)
            
            # Get activities that have been submitted
            assignments = LearningActivity.query.filter(
                LearningActivity.id.in_(completed_activity_ids)
            ).order_by(LearningActivity.due_date.desc()).all()
            
            # Get submissions for these activities
            for sub in user_subs_all:
                if sub.activity_id:
                    if sub.activity_id not in activity_submissions:
                        activity_submissions[sub.activity_id] = []
                    activity_submissions[sub.activity_id].append(sub)
        
        return render_template('history.html', 
                             submissions=submissions, 
                             quizzes=quizzes,
                             assignments=assignments if filter_type == 'assignments' else [],
                             activity_submissions=activity_submissions if filter_type == 'assignments' else {},
                             now=datetime.utcnow())

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
        
        # Load activity if submission is part of an assignment
        if sub.activity_id:
            sub.activity = LearningActivity.query.get(sub.activity_id)
        
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
                # Use GradingService to update grade (this automatically sets instructor_approved=True)
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

    # --- ADMIN ROUTES ---
    
    @app.route('/admin/dashboard')
    @role_required('Admin')
    def admin_dashboard():
        stats = AdminService.get_user_statistics()
        recent_users = AdminRepository.get_all_users()[:10]
        recent_courses = AdminRepository.get_all_courses()[:5]
        return render_template('admin_dashboard.html', stats=stats, recent_users=recent_users, recent_courses=recent_courses)
    
    @app.route('/admin/users')
    @role_required('Admin')
    def admin_users():
        users = AdminRepository.get_all_users()
        role_filter = request.args.get('role', 'all')
        if role_filter != 'all':
            users = [u for u in users if u.role == role_filter]
        return render_template('admin_users.html', users=users, role_filter=role_filter)
    
    @app.route('/admin/users/create', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_create_user():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'Student')
            
            errors = AdminService.validate_user_data(username, email, password, role)
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('admin_user_create.html')
            
            try:
                AdminRepository.create_user(username, email, password, role)
                flash('User created successfully!', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                flash(f'Error creating user: {str(e)}', 'danger')
        
        return render_template('admin_user_create.html')
    
    @app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_edit_user(user_id):
        user = AdminRepository.get_user_by_id(user_id)
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')  # Optional
            role = request.form.get('role')
            
            # Validate (skip password if not provided)
            errors = AdminService.validate_user_data(username, email, None if not password else password, role)
            # Remove password error if password is empty
            if not password:
                errors = [e for e in errors if 'Password' not in e]
            # Check if username/email conflicts with other users
            existing_username = User.query.filter_by(username=username).first()
            if existing_username and existing_username.id != user_id:
                errors.append("Username already exists")
            existing_email = User.query.filter_by(email=email).first()
            if existing_email and existing_email.id != user_id:
                errors.append("Email already exists")
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('admin_user_edit.html', user=user)
            
            try:
                AdminRepository.update_user(user_id, username, email, password if password else None, role)
                flash('User updated successfully!', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                flash(f'Error updating user: {str(e)}', 'danger')
        
        return render_template('admin_user_edit.html', user=user)
    
    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @role_required('Admin')
    def admin_delete_user(user_id):
        if user_id == current_user.id:
            flash('You cannot delete your own account', 'danger')
            return redirect(url_for('admin_users'))
        
        try:
            AdminRepository.delete_user(user_id)
            flash('User deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}', 'danger')
        
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/courses')
    @role_required('Admin')
    def admin_courses():
        courses = AdminRepository.get_all_courses()
        instructors = AdminRepository.get_users_by_role('Instructor')
        return render_template('admin_courses.html', courses=courses, instructors=instructors)
    
    @app.route('/admin/courses/create', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_create_course():
        instructors = AdminRepository.get_users_by_role('Instructor')
        
        if request.method == 'POST':
            name = request.form.get('name')
            code = request.form.get('code')
            description = request.form.get('description')
            instructor_id = request.form.get('instructor_id', type=int) or None
            is_active = request.form.get('is_active') == 'on'
            
            errors = AdminService.validate_course_data(name, code, description)
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('admin_course_create.html', instructors=instructors)
            
            try:
                AdminRepository.create_course(name, code, description, instructor_id, is_active)
                flash('Course created successfully!', 'success')
                return redirect(url_for('admin_courses'))
            except Exception as e:
                flash(f'Error creating course: {str(e)}', 'danger')
        
        return render_template('admin_course_create.html', instructors=instructors)
    
    @app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_edit_course(course_id):
        course = AdminRepository.get_course_by_id(course_id)
        if not course:
            flash('Course not found', 'danger')
            return redirect(url_for('admin_courses'))
        
        instructors = AdminRepository.get_users_by_role('Instructor')
        
        if request.method == 'POST':
            name = request.form.get('name')
            code = request.form.get('code')
            description = request.form.get('description')
            instructor_id = request.form.get('instructor_id', type=int) or None
            is_active = request.form.get('is_active') == 'on'
            
            errors = AdminService.validate_course_data(name, code, description)
            # Check if code conflicts with other courses
            existing_course = Course.query.filter_by(code=code).first()
            if existing_course and existing_course.id != course_id:
                errors.append("Course code already exists")
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('admin_course_edit.html', course=course, instructors=instructors)
            
            try:
                AdminRepository.update_course(course_id, name, code, description, instructor_id, is_active)
                flash('Course updated successfully!', 'success')
                return redirect(url_for('admin_courses'))
            except Exception as e:
                flash(f'Error updating course: {str(e)}', 'danger')
        
        return render_template('admin_course_edit.html', course=course, instructors=instructors)
    
    @app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
    @role_required('Admin')
    def admin_delete_course(course_id):
        try:
            AdminRepository.delete_course(course_id)
            flash('Course deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting course: {str(e)}', 'danger')
        
        return redirect(url_for('admin_courses'))
    
    @app.route('/admin/enrollments')
    @role_required('Admin')
    def admin_enrollments():
        enrollments = AdminRepository.get_all_enrollments()
        course_filter = request.args.get('course_id', type=int)
        student_filter = request.args.get('student_id', type=int)
        
        if course_filter:
            enrollments = [e for e in enrollments if e.course_id == course_filter]
        if student_filter:
            enrollments = [e for e in enrollments if e.student_id == student_filter]
        
        courses = AdminRepository.get_all_courses()
        students = AdminRepository.get_users_by_role('Student')
        
        return render_template('admin_enrollments.html', 
                             enrollments=enrollments, 
                             courses=courses, 
                             students=students,
                             course_filter=course_filter,
                             student_filter=student_filter)
    
    @app.route('/admin/enrollments/create', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_create_enrollment():
        courses = AdminRepository.get_all_courses()
        students = AdminRepository.get_users_by_role('Student')
        
        if request.method == 'POST':
            student_id = request.form.get('student_id', type=int)
            course_id = request.form.get('course_id', type=int)
            status = request.form.get('status', 'active')
            
            if not student_id or not course_id:
                flash('Student and course are required', 'danger')
                return render_template('admin_enrollment_create.html', courses=courses, students=students)
            
            try:
                result = AdminRepository.create_enrollment(student_id, course_id, status)
                if result:
                    flash('Enrollment created successfully!', 'success')
                    return redirect(url_for('admin_enrollments'))
                else:
                    flash('Student is already enrolled in this course', 'danger')
            except Exception as e:
                flash(f'Error creating enrollment: {str(e)}', 'danger')
        
        return render_template('admin_enrollment_create.html', courses=courses, students=students)
    
    @app.route('/admin/enrollments/<int:enrollment_id>/edit', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_edit_enrollment(enrollment_id):
        enrollment = AdminRepository.get_enrollment_by_id(enrollment_id)
        if not enrollment:
            flash('Enrollment not found', 'danger')
            return redirect(url_for('admin_enrollments'))
        
        if request.method == 'POST':
            status = request.form.get('status')
            
            try:
                AdminRepository.update_enrollment(enrollment_id, status)
                flash('Enrollment updated successfully!', 'success')
                return redirect(url_for('admin_enrollments'))
            except Exception as e:
                flash(f'Error updating enrollment: {str(e)}', 'danger')
        
        return render_template('admin_enrollment_edit.html', enrollment=enrollment)
    
    @app.route('/admin/enrollments/<int:enrollment_id>/delete', methods=['POST'])
    @role_required('Admin')
    def admin_delete_enrollment(enrollment_id):
        try:
            AdminRepository.delete_enrollment(enrollment_id)
            flash('Enrollment deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting enrollment: {str(e)}', 'danger')
        
        return redirect(url_for('admin_enrollments'))
    
    @app.route('/admin/settings')
    @role_required('Admin')
    def admin_settings():
        settings = AdminRepository.get_all_settings()
        return render_template('admin_settings.html', settings=settings)
    
    @app.route('/admin/settings/update', methods=['POST'])
    @role_required('Admin')
    def admin_update_setting():
        setting_key = request.form.get('setting_key')
        setting_value = request.form.get('setting_value')
        setting_type = request.form.get('setting_type', 'string')
        description = request.form.get('description')
        
        if not setting_key:
            flash('Setting key is required', 'danger')
            return redirect(url_for('admin_settings'))
        
        try:
            AdminRepository.create_or_update_setting(setting_key, setting_value, setting_type, description, current_user.id)
            flash('Setting updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating setting: {str(e)}', 'danger')
        
        return redirect(url_for('admin_settings'))
    
    @app.route('/admin/ai-integrations')
    @role_required('Admin')
    def admin_ai_integrations():
        integrations = AdminRepository.get_all_ai_integrations()
        return render_template('admin_ai_integrations.html', integrations=integrations)
    
    @app.route('/admin/ai-integrations/create', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_create_ai_integration():
        if request.method == 'POST':
            integration_name = request.form.get('integration_name')
            api_key = request.form.get('api_key')
            is_active = request.form.get('is_active') == 'on'
            api_endpoint = request.form.get('api_endpoint')
            configuration = request.form.get('configuration')
            
            if not integration_name:
                flash('Integration name is required', 'danger')
                return render_template('admin_ai_integration_create.html')
            
            try:
                AdminRepository.create_or_update_ai_integration(
                    integration_name, api_key, is_active, api_endpoint, configuration, current_user.id
                )
                flash('AI integration configured successfully!', 'success')
                return redirect(url_for('admin_ai_integrations'))
            except Exception as e:
                flash(f'Error configuring AI integration: {str(e)}', 'danger')
        
        return render_template('admin_ai_integration_create.html')
    
    @app.route('/admin/ai-integrations/<int:integration_id>/edit', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_edit_ai_integration(integration_id):
        integration = AdminRepository.get_ai_integration_by_id(integration_id)
        if not integration:
            flash('AI integration not found', 'danger')
            return redirect(url_for('admin_ai_integrations'))
        
        if request.method == 'POST':
            api_key = request.form.get('api_key')
            is_active = request.form.get('is_active') == 'on'
            api_endpoint = request.form.get('api_endpoint')
            configuration = request.form.get('configuration')
            
            # Only update API key if provided (not empty)
            api_key_to_update = api_key if api_key and api_key.strip() else None
            
            try:
                AdminRepository.create_or_update_ai_integration(
                    integration.integration_name, api_key_to_update, is_active, api_endpoint, configuration, current_user.id
                )
                flash('AI integration updated successfully!', 'success')
                return redirect(url_for('admin_ai_integrations'))
            except Exception as e:
                flash(f'Error updating AI integration: {str(e)}', 'danger')
        
        return render_template('admin_ai_integration_edit.html', integration=integration)
    
    @app.route('/admin/ai-integrations/<int:integration_id>/toggle', methods=['POST'])
    @role_required('Admin')
    def admin_toggle_ai_integration(integration_id):
        integration = AdminRepository.get_ai_integration_by_id(integration_id)
        if integration:
            try:
                AdminRepository.create_or_update_ai_integration(
                    integration.integration_name, None, not integration.is_active, 
                    None, None, current_user.id
                )
                status = "activated" if not integration.is_active else "deactivated"
                flash(f'AI integration {status} successfully!', 'success')
            except Exception as e:
                flash(f'Error toggling AI integration: {str(e)}', 'danger')
        
        return redirect(url_for('admin_ai_integrations'))
    
    # --- LMS Integration Routes (UC15, FR20) ---
    @app.route('/admin/lms-integrations')
    @role_required('Admin')
    def admin_lms_integrations():
        integrations = AdminRepository.get_all_lms_integrations()
        return render_template('admin_lms_integrations.html', integrations=integrations)
    
    @app.route('/admin/lms-integrations/create', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_create_lms_integration():
        if request.method == 'POST':
            lms_type = request.form.get('lms_type')
            lms_name = request.form.get('lms_name')
            api_url = request.form.get('api_url')
            api_key = request.form.get('api_key')
            api_secret = request.form.get('api_secret')
            course_id = request.form.get('course_id')
            is_active = request.form.get('is_active') == 'on'
            sync_enabled = request.form.get('sync_enabled') == 'on'
            configuration = request.form.get('configuration')
            
            if not lms_type or not lms_name or not api_url:
                flash('LMS type, name, and API URL are required', 'danger')
                return render_template('admin_lms_integration_create.html')
            
            try:
                AdminRepository.create_or_update_lms_integration(
                    lms_type, lms_name, api_url, api_key, api_secret, course_id,
                    is_active, sync_enabled, configuration, current_user.id
                )
                flash('LMS integration configured successfully!', 'success')
                return redirect(url_for('admin_lms_integrations'))
            except Exception as e:
                flash(f'Error configuring LMS integration: {str(e)}', 'danger')
        
        return render_template('admin_lms_integration_create.html')
    
    @app.route('/admin/lms-integrations/<int:integration_id>/edit', methods=['GET', 'POST'])
    @role_required('Admin')
    def admin_edit_lms_integration(integration_id):
        integration = AdminRepository.get_lms_integration_by_id(integration_id)
        if not integration:
            flash('LMS integration not found', 'danger')
            return redirect(url_for('admin_lms_integrations'))
        
        if request.method == 'POST':
            lms_name = request.form.get('lms_name')
            api_url = request.form.get('api_url')
            api_key = request.form.get('api_key')
            api_secret = request.form.get('api_secret')
            course_id = request.form.get('course_id')
            is_active = request.form.get('is_active') == 'on'
            sync_enabled = request.form.get('sync_enabled') == 'on'
            configuration = request.form.get('configuration')
            
            # Only update API key if provided (not empty)
            api_key_to_update = api_key if api_key and api_key.strip() else None
            api_secret_to_update = api_secret if api_secret and api_secret.strip() else None
            
            try:
                AdminRepository.create_or_update_lms_integration(
                    integration.lms_type, lms_name, api_url, api_key_to_update, api_secret_to_update,
                    course_id, is_active, sync_enabled, configuration, current_user.id
                )
                flash('LMS integration updated successfully!', 'success')
                return redirect(url_for('admin_lms_integrations'))
            except Exception as e:
                flash(f'Error updating LMS integration: {str(e)}', 'danger')
        
        return render_template('admin_lms_integration_edit.html', integration=integration)
    
    @app.route('/admin/lms-integrations/<int:integration_id>/delete', methods=['POST'])
    @role_required('Admin')
    def admin_delete_lms_integration(integration_id):
        try:
            AdminRepository.delete_lms_integration(integration_id)
            flash('LMS integration deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting LMS integration: {str(e)}', 'danger')
        
        return redirect(url_for('admin_lms_integrations'))
    
    @app.route('/admin/lms-integrations/<int:integration_id>/sync', methods=['POST'])
    @role_required('Admin')
    def admin_sync_lms_grades(integration_id):
        from services.lms_service import LMSService
        student_id = request.form.get('student_id', type=int)
        submission_id = request.form.get('submission_id', type=int)
        
        try:
            result = LMSService.sync_grades_to_lms(integration_id, student_id, submission_id)
            if result.get('success'):
                flash(result.get('message', 'Grades synced successfully!'), 'success')
            else:
                flash(result.get('message', 'Failed to sync grades'), 'danger')
        except Exception as e:
            flash(f'Error syncing grades: {str(e)}', 'danger')
        
        return redirect(url_for('admin_lms_integrations'))
    
    # --- Adaptive Insights Route (UC17) ---
    @app.route('/admin/generate-insights', methods=['POST'])
    @role_required('Admin')
    def admin_generate_insights():
        from services.adaptive_insights_service import AdaptiveInsightsService
        
        try:
            result = AdaptiveInsightsService.generate_insights_for_all_students()
            flash(f'Generated insights for {result["success_count"]}/{result["total_students"]} students. Total insights: {result["total_insights"]}', 'success')
        except Exception as e:
            flash(f'Error generating insights: {str(e)}', 'danger')
        
        return redirect(url_for('admin_dashboard'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
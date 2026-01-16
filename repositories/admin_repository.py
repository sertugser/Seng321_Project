from models.entities import User, Course, Enrollment, PlatformSettings, AIIntegration, LMSIntegration
from models.database import db
from werkzeug.security import generate_password_hash

class AdminRepository:
    @staticmethod
    def get_all_users():
        return User.query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_user_by_id(user_id):
        return User.query.filter_by(id=user_id).first()
    
    @staticmethod
    def get_users_by_role(role):
        return User.query.filter_by(role=role).all()
    
    @staticmethod
    def create_user(username, email, password, role='Student'):
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        return new_user
    
    @staticmethod
    def update_user(user_id, username=None, email=None, password=None, role=None):
        # Use filter_by with explicit ID to ensure we get the correct user
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return None
        
        # Always update if provided (not None)
        if username is not None:
            user.username = username.strip() if isinstance(username, str) else username
        if email is not None:
            user.email = email.strip() if isinstance(email, str) else email
        if password is not None and password:
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
        # Always update role if provided (even if empty string, but should not be None for updates)
        if role is not None:
            user.role = role.strip() if isinstance(role, str) else role
        
        # Only commit the specific user object, not the entire session
        db.session.add(user)
        db.session.commit()
        # Refresh to ensure we have the latest data
        db.session.refresh(user)
        return user
    
    @staticmethod
    def delete_user(user_id):
        from models.entities import Submission, Grade, LearningGoal, Quiz, QuizDetail, Enrollment, LearningActivity, Course, AdaptiveInsight
        
        user = User.query.get(user_id)
        if not user:
            return False
        
        try:
            # 1. Delete user's submissions and their grades (as student)
            submissions = Submission.query.filter_by(student_id=user_id).all()
            for submission in submissions:
                if submission.grade:
                    db.session.delete(submission.grade)
                db.session.delete(submission)
            
            # 2. Delete activities created by user (as instructor)
            # Must delete before submissions that reference them
            activities_as_instructor = LearningActivity.query.filter_by(instructor_id=user_id).all()
            for activity in activities_as_instructor:
                # Delete all submissions and grades for these activities (from all students)
                activity_submissions = Submission.query.filter_by(activity_id=activity.id).all()
                for sub in activity_submissions:
                    if sub.grade:
                        db.session.delete(sub.grade)
                    db.session.delete(sub)
                db.session.delete(activity)
            
            # 3. Delete activities assigned to user (as student) - set student_id to NULL
            activities_as_student = LearningActivity.query.filter_by(student_id=user_id).all()
            for activity in activities_as_student:
                activity.student_id = None
            
            # 4. Delete user's learning goals
            goals = LearningGoal.query.filter_by(user_id=user_id).all()
            for goal in goals:
                db.session.delete(goal)
            
            # 5. Delete user's quizzes and their details
            quizzes = Quiz.query.filter_by(user_id=user_id).all()
            for quiz in quizzes:
                quiz_details = QuizDetail.query.filter_by(quiz_id=quiz.id).all()
                for detail in quiz_details:
                    db.session.delete(detail)
                db.session.delete(quiz)
            
            # 6. Delete user's enrollments
            enrollments = Enrollment.query.filter_by(student_id=user_id).all()
            for enrollment in enrollments:
                db.session.delete(enrollment)
            
            # 7. Update courses taught by user (as instructor) - set instructor_id to NULL
            courses = Course.query.filter_by(instructor_id=user_id).all()
            for course in courses:
                course.instructor_id = None
            
            # 8. Delete adaptive insights
            insights = AdaptiveInsight.query.filter_by(user_id=user_id).all()
            for insight in insights:
                db.session.delete(insight)
            
            # Note: PlatformSettings, AIIntegration, LMSIntegration have updated_by as nullable,
            # so we don't need to update them - they can keep the user_id even after deletion
            
            # 9. Finally delete the user
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_all_courses():
        return Course.query.order_by(Course.created_at.desc()).all()
    
    @staticmethod
    def get_course_by_id(course_id):
        return Course.query.filter_by(id=course_id).first()
    
    @staticmethod
    def create_course(name, code, description=None, instructor_id=None, is_active=True):
        new_course = Course(
            name=name,
            code=code,
            description=description,
            instructor_id=instructor_id,
            is_active=is_active
        )
        db.session.add(new_course)
        db.session.commit()
        return new_course
    
    @staticmethod
    def update_course(course_id, name=None, code=None, description=None, instructor_id=None, is_active=None):
        # Use filter_by with explicit ID to ensure we get the correct course
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return None
        
        # Always update if provided (not None) - name and code are required fields from form
        if name is not None:
            course.name = name.strip() if isinstance(name, str) else name
        if code is not None:
            course.code = code.strip() if isinstance(code, str) else code
        # Description can be empty string, so check for None explicitly
        if description is not None:
            course.description = description.strip() if isinstance(description, str) else description
        if instructor_id is not None:
            course.instructor_id = instructor_id
        if is_active is not None:
            course.is_active = is_active
        
        # Commit changes (course is already in session, no need to add)
        db.session.commit()
        # Refresh to ensure we have the latest data
        db.session.refresh(course)
        return course
    
    @staticmethod
    def delete_course(course_id):
        course = Course.query.get(course_id)
        if course:
            db.session.delete(course)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_all_enrollments():
        return Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
    
    @staticmethod
    def get_enrollment_by_id(enrollment_id):
        return Enrollment.query.get(enrollment_id)
    
    @staticmethod
    def get_enrollments_by_course(course_id):
        return Enrollment.query.filter_by(course_id=course_id).all()
    
    @staticmethod
    def get_enrollments_by_student(student_id):
        return Enrollment.query.filter_by(student_id=student_id).all()
    
    @staticmethod
    def create_enrollment(student_id, course_id, status='active'):
        # Check if enrollment already exists
        existing = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
        if existing:
            return None
        
        new_enrollment = Enrollment(
            student_id=student_id,
            course_id=course_id,
            status=status
        )
        db.session.add(new_enrollment)
        db.session.commit()
        return new_enrollment
    
    @staticmethod
    def update_enrollment(enrollment_id, status=None):
        enrollment = Enrollment.query.get(enrollment_id)
        if not enrollment:
            return None
        
        if status:
            enrollment.status = status
        
        db.session.commit()
        return enrollment
    
    @staticmethod
    def delete_enrollment(enrollment_id):
        enrollment = Enrollment.query.get(enrollment_id)
        if enrollment:
            db.session.delete(enrollment)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_all_settings():
        return PlatformSettings.query.order_by(PlatformSettings.setting_key).all()
    
    @staticmethod
    def get_setting_by_key(setting_key):
        return PlatformSettings.query.filter_by(setting_key=setting_key).first()
    
    @staticmethod
    def create_or_update_setting(setting_key, setting_value, setting_type='string', description=None, updated_by=None):
        setting = PlatformSettings.query.filter_by(setting_key=setting_key).first()
        
        if setting:
            setting.setting_value = setting_value
            setting.setting_type = setting_type
            if description:
                setting.description = description
            if updated_by:
                setting.updated_by = updated_by
        else:
            setting = PlatformSettings(
                setting_key=setting_key,
                setting_value=setting_value,
                setting_type=setting_type,
                description=description,
                updated_by=updated_by
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting
    
    @staticmethod
    def get_all_ai_integrations():
        return AIIntegration.query.order_by(AIIntegration.integration_name).all()
    
    @staticmethod
    def get_ai_integration_by_id(integration_id):
        return AIIntegration.query.get(integration_id)
    
    @staticmethod
    def get_ai_integration_by_name(integration_name):
        return AIIntegration.query.filter_by(integration_name=integration_name).first()
    
    @staticmethod
    def create_or_update_ai_integration(integration_name, api_key=None, is_active=False, 
                                       api_endpoint=None, configuration=None, updated_by=None):
        integration = AIIntegration.query.filter_by(integration_name=integration_name).first()
        
        if integration:
            # Only update API key if a new value is provided (not None and not empty)
            if api_key is not None and api_key.strip():
                integration.api_key = api_key
            integration.is_active = is_active
            if api_endpoint is not None:
                integration.api_endpoint = api_endpoint
            if configuration is not None:
                integration.configuration = configuration
            if updated_by:
                integration.updated_by = updated_by
        else:
            integration = AIIntegration(
                integration_name=integration_name,
                api_key=api_key,
                is_active=is_active,
                api_endpoint=api_endpoint,
                configuration=configuration,
                updated_by=updated_by
            )
            db.session.add(integration)
        
        db.session.commit()
        return integration
    
    # --- LMS Integration Methods (UC15, FR20) ---
    @staticmethod
    def get_all_lms_integrations():
        return LMSIntegration.query.order_by(LMSIntegration.lms_type).all()
    
    @staticmethod
    def get_lms_integration_by_id(integration_id):
        return LMSIntegration.query.get(integration_id)
    
    @staticmethod
    def get_lms_integration_by_type(lms_type):
        return LMSIntegration.query.filter_by(lms_type=lms_type).first()
    
    @staticmethod
    def create_or_update_lms_integration(lms_type, lms_name, api_url, api_key=None, api_secret=None,
                                        course_id=None, is_active=False, sync_enabled=False,
                                        configuration=None, updated_by=None):
        integration = LMSIntegration.query.filter_by(lms_type=lms_type, course_id=course_id).first()
        
        if integration:
            integration.lms_name = lms_name
            integration.api_url = api_url
            if api_key is not None and api_key.strip():
                integration.api_key = api_key
            if api_secret is not None and api_secret.strip():
                integration.api_secret = api_secret
            if course_id is not None:
                integration.course_id = course_id
            integration.is_active = is_active
            integration.sync_enabled = sync_enabled
            if configuration is not None:
                integration.configuration = configuration
            if updated_by:
                integration.updated_by = updated_by
        else:
            integration = LMSIntegration(
                lms_type=lms_type,
                lms_name=lms_name,
                api_url=api_url,
                api_key=api_key,
                api_secret=api_secret,
                course_id=course_id,
                is_active=is_active,
                sync_enabled=sync_enabled,
                configuration=configuration,
                updated_by=updated_by
            )
            db.session.add(integration)
        
        db.session.commit()
        return integration
    
    @staticmethod
    def delete_lms_integration(integration_id):
        integration = LMSIntegration.query.get(integration_id)
        if integration:
            db.session.delete(integration)
            db.session.commit()
            return True
        return False
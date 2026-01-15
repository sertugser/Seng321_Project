from models.entities import User, Course, Enrollment, PlatformSettings, AIIntegration, LMSIntegration
from models.database import db
from werkzeug.security import generate_password_hash

class AdminRepository:
    @staticmethod
    def get_all_users():
        return User.query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)
    
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
        user = User.query.get(user_id)
        if not user:
            return None
        
        if username:
            user.username = username
        if email:
            user.email = email
        if password:
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
        if role:
            user.role = role
        
        db.session.commit()
        return user
    
    @staticmethod
    def delete_user(user_id):
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_all_courses():
        return Course.query.order_by(Course.created_at.desc()).all()
    
    @staticmethod
    def get_course_by_id(course_id):
        return Course.query.get(course_id)
    
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
        course = Course.query.get(course_id)
        if not course:
            return None
        
        if name:
            course.name = name
        if code:
            course.code = code
        if description is not None:
            course.description = description
        if instructor_id is not None:
            course.instructor_id = instructor_id
        if is_active is not None:
            course.is_active = is_active
        
        db.session.commit()
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
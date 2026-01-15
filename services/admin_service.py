from repositories.admin_repository import AdminRepository
from models.entities import User, Course, Enrollment

class AdminService:
    @staticmethod
    def get_user_statistics():
        """Get platform statistics for admin dashboard"""
        all_users = AdminRepository.get_all_users()
        students = [u for u in all_users if u.role == 'Student']
        instructors = [u for u in all_users if u.role == 'Instructor']
        admins = [u for u in all_users if u.role == 'Admin']
        
        all_courses = AdminRepository.get_all_courses()
        all_enrollments = AdminRepository.get_all_enrollments()
        active_enrollments = [e for e in all_enrollments if e.status == 'active']
        
        return {
            'total_users': len(all_users),
            'total_students': len(students),
            'total_instructors': len(instructors),
            'total_admins': len(admins),
            'total_courses': len(all_courses),
            'total_enrollments': len(all_enrollments),
            'active_enrollments': len(active_enrollments)
        }
    
    @staticmethod
    def validate_user_data(username, email, password=None, role=None):
        """Validate user data before creation/update"""
        errors = []
        
        if not username or len(username.strip()) == 0:
            errors.append("Username is required")
        elif len(username) > 50:
            errors.append("Username must be 50 characters or less")
        
        if not email or len(email.strip()) == 0:
            errors.append("Email is required")
        elif '@' not in email:
            errors.append("Invalid email format")
        
        if password and len(password) < 6:
            errors.append("Password must be at least 6 characters")
        
        if role and role not in ['Student', 'Instructor', 'Admin']:
            errors.append("Invalid role. Must be Student, Instructor, or Admin")
        
        # Check for duplicates
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            errors.append("Username already exists")
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            errors.append("Email already exists")
        
        return errors
    
    @staticmethod
    def validate_course_data(name, code, description=None):
        """Validate course data"""
        errors = []
        
        if not name or len(name.strip()) == 0:
            errors.append("Course name is required")
        
        if not code or len(code.strip()) == 0:
            errors.append("Course code is required")
        
        # Check for duplicate code
        existing_course = Course.query.filter_by(code=code).first()
        if existing_course:
            errors.append("Course code already exists")
        
        return errors
    
    @staticmethod
    def get_course_statistics(course_id):
        """Get statistics for a specific course"""
        course = AdminRepository.get_course_by_id(course_id)
        if not course:
            return None
        
        enrollments = AdminRepository.get_enrollments_by_course(course_id)
        active_enrollments = [e for e in enrollments if e.status == 'active']
        
        return {
            'course': course,
            'total_enrollments': len(enrollments),
            'active_enrollments': len(active_enrollments),
            'completed_enrollments': len([e for e in enrollments if e.status == 'completed']),
            'dropped_enrollments': len([e for e in enrollments if e.status == 'dropped'])
        }
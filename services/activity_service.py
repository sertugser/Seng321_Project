from models.entities import LearningActivity, Course
from models.database import db
from datetime import datetime

class ActivityService:
    @staticmethod
    def create_new_activity(instructor_id, title, activity_type, description=None, due_date=None, student_id=None, quiz_category=None, course_ids=None, attachment_path=None, attachment_filename=None):
        """
        Create a new learning activity
        Args:
            instructor_id: ID of the instructor creating the activity
            title: Activity title
            activity_type: Type of activity (WRITING, SPEAKING, QUIZ, HANDWRITTEN)
            description: Optional description
            due_date: Optional due date
            student_id: Optional student ID - if None, activity is assigned to all students
            quiz_category: Optional quiz category (for QUIZ type activities)
            course_ids: Optional list of course IDs to assign this activity to
            attachment_path: Optional path to uploaded attachment file
            attachment_filename: Optional original filename of attachment
        """
        new_activity = LearningActivity(
            instructor_id=instructor_id,
            student_id=student_id,  # None = assigned to all students
            title=title,
            activity_type=activity_type,
            description=description,
            quiz_category=quiz_category,
            due_date=due_date,
            attachment_path=attachment_path,
            attachment_filename=attachment_filename
        )
        db.session.add(new_activity)
        db.session.flush()  # Flush to get the ID
        
        # Assign to courses if provided
        if course_ids:
            courses = Course.query.filter(Course.id.in_(course_ids)).all()
            new_activity.courses = courses
        
        db.session.commit()
        return new_activity
    
    @staticmethod
    def update_activity_courses(activity_id, course_ids):
        """
        Update the courses assigned to an activity
        Args:
            activity_id: ID of the activity
            course_ids: List of course IDs to assign this activity to
        """
        activity = LearningActivity.query.get(activity_id)
        if not activity:
            return False
        
        if course_ids:
            courses = Course.query.filter(Course.id.in_(course_ids)).all()
            activity.courses = courses
        else:
            activity.courses = []
        
        db.session.commit()
        return True
    
    @staticmethod
    def assign_to_class(activity_id, student_ids):
        """
        Assign activity to students
        For now, this is handled by activity_id in submissions
        In a full implementation, there would be an Assignment table
        """
        # This would typically create Assignment records
        # For now, we'll just return success
        return True
    
    @staticmethod
    def get_activities_for_student(student_id):
        """
        Get activities available for a student
        Returns activities where student_id is None (all students) or matches the student_id
        """
        return LearningActivity.query.filter(
            (LearningActivity.student_id == None) | (LearningActivity.student_id == student_id)
        ).filter(
            (LearningActivity.due_date == None) | (LearningActivity.due_date >= datetime.utcnow())
        ).order_by(LearningActivity.due_date.asc()).all()
    
    @staticmethod
    def get_activities_by_instructor(instructor_id):
        """
        Get all activities created by an instructor
        """
        return LearningActivity.query.filter_by(instructor_id=instructor_id).order_by(LearningActivity.created_at.desc()).all()








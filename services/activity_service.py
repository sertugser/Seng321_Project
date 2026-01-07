from models.entities import LearningActivity
from models.database import db
from datetime import datetime

class ActivityService:
    @staticmethod
    def create_new_activity(instructor_id, title, activity_type, description=None, due_date=None):
        """
        Create a new learning activity
        """
        new_activity = LearningActivity(
            instructor_id=instructor_id,
            title=title,
            activity_type=activity_type,
            description=description,
            due_date=due_date
        )
        db.session.add(new_activity)
        db.session.commit()
        return new_activity
    
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
        """
        return LearningActivity.query.filter(
            LearningActivity.due_date >= datetime.utcnow()
        ).order_by(LearningActivity.due_date.asc()).all()
    
    @staticmethod
    def get_activities_by_instructor(instructor_id):
        """
        Get all activities created by an instructor
        """
        return LearningActivity.query.filter_by(instructor_id=instructor_id).order_by(LearningActivity.created_at.desc()).all()







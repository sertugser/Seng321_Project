from models.entities import LearningActivity
from models.database import db
from datetime import datetime

class ActivityRepository:
    @staticmethod
    def save_activity(activity):
        """
        Save activity to database
        """
        db.session.add(activity)
        db.session.commit()
        return activity
    
    @staticmethod
    def get_activity_by_id(activity_id):
        """
        Get activity by ID
        """
        return LearningActivity.query.get(activity_id)
    
    @staticmethod
    def get_all_activities():
        """
        Get all activities
        """
        return LearningActivity.query.order_by(LearningActivity.due_date.asc()).all()
    
    @staticmethod
    def get_pending_activities():
        """
        Get activities with future due dates
        """
        return LearningActivity.query.filter(
            LearningActivity.due_date >= datetime.utcnow()
        ).order_by(LearningActivity.due_date.asc()).all()







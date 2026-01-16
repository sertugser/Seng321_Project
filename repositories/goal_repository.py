from models.entities import LearningGoal
from models.database import db

class GoalRepository:
    @staticmethod
    def save_goal(goal):
        """
        Save goal to database
        """
        db.session.add(goal)
        db.session.commit()
        return goal
    
    @staticmethod
    def get_goal_by_id(goal_id):
        """
        Get goal by ID
        """
        return LearningGoal.query.get(goal_id)
    
    @staticmethod
    def get_goals_by_user(user_id):
        """
        Get all goals for a user
        """
        return LearningGoal.query.filter_by(user_id=user_id).order_by(LearningGoal.created_at.desc()).all()
    
    @staticmethod
    def get_active_goals_by_user(user_id):
        """
        Get active (In Progress) goals for a user
        """
        return LearningGoal.query.filter_by(
            user_id=user_id,
            status='In Progress'
        ).order_by(LearningGoal.created_at.desc()).all()
    
    @staticmethod
    def update_goal(goal_id, **kwargs):
        """
        Update goal fields
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            for key, value in kwargs.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
                    # Keep goal_name in sync with title
                    if key == 'title' and value is not None:
                        goal.goal_name = str(value).strip()
            db.session.commit()
            return goal
        return None
    
    @staticmethod
    def delete_goal(goal_id):
        """
        Delete a goal
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            db.session.delete(goal)
            db.session.commit()
            return True
        return False

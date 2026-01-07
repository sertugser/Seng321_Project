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
        return LearningGoal.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def update_goal(goal_id, current_value=None, target_value=None):
        """
        Update goal values
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            if current_value is not None:
                goal.current_value = current_value
            if target_value is not None:
                goal.target_value = target_value
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







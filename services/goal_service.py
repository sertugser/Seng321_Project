from models.entities import LearningGoal
from models.database import db

class GoalService:
    @staticmethod
    def set_goal(user_id, goal_name, target_value, current_value=0, category='General'):
        """
        Set a new learning goal for user
        """
        new_goal = LearningGoal(
            user_id=user_id,
            goal_name=goal_name,
            target_value=target_value,
            current_value=current_value,
            category=category
        )
        db.session.add(new_goal)
        db.session.commit()
        return new_goal
    
    @staticmethod
    def update_goal(goal_id, goal_name=None, target_value=None, current_value=None, category=None):
        """
        Update a goal
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            if goal_name is not None:
                goal.goal_name = goal_name
            if target_value is not None:
                goal.target_value = target_value
            if current_value is not None:
                goal.current_value = current_value
            if category is not None:
                goal.category = category
            db.session.commit()
            return goal
        return None
    
    @staticmethod
    def track_goal_progress(goal_id, new_current_value):
        """
        Update goal progress
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            goal.current_value = new_current_value
            db.session.commit()
            return goal
        return None
    
    @staticmethod
    def get_user_goals(user_id):
        """
        Get all goals for a user
        """
        return LearningGoal.query.filter_by(user_id=user_id).all()
    
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








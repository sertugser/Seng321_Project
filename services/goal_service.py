from models.entities import LearningGoal, Quiz, Grade, Submission
from models.database import db
from datetime import datetime
import traceback

class GoalService:
    @staticmethod
    def create_goal(user_id, title, category, target_score, current_score=0.0, target_date=None):
        """
        Create a new learning goal for user
        Args:
            user_id: ID of the user
            title: Goal title (e.g., "Improve Writing Coherence")
            category: Category (Writing, Speaking, Quiz)
            target_score: Target score (0-100)
            current_score: Initial current score (default 0.0)
            target_date: Optional deadline date (datetime object or None)
        """
        try:
            # Validate inputs
            if not user_id:
                raise ValueError("user_id is required")
            if not title or not title.strip():
                raise ValueError("title is required")
            if not category:
                raise ValueError("category is required")
            if target_score is None:
                raise ValueError("target_score is required")
            if not isinstance(target_score, (int, float)):
                raise ValueError(f"target_score must be a number, got {type(target_score)}")
            if target_score < 0 or target_score > 100:
                raise ValueError(f"target_score must be between 0 and 100, got {target_score}")
            
            # Ensure target_score is float
            target_score = float(target_score)
            current_score = float(current_score) if current_score is not None else 0.0
            
            # Validate target_date is datetime or None
            if target_date is not None and not isinstance(target_date, datetime):
                raise ValueError(f"target_date must be a datetime object or None, got {type(target_date)}")
            
            title_str = str(title).strip()
            new_goal = LearningGoal(
                user_id=int(user_id),
                title=title_str,
                goal_name=title_str,  # Set goal_name to same value as title for backward compatibility
                category=str(category),
                target_score=target_score,
                current_score=current_score,
                status='In Progress',
                target_date=target_date
            )
            db.session.add(new_goal)
            db.session.commit()
            return new_goal
        except Exception as e:
            # Log detailed error
            error_traceback = traceback.format_exc()
            print("=" * 80)
            print("ERROR IN GoalService.create_goal - Full Traceback:")
            print(error_traceback)
            print("=" * 80)
            print(f"Error message: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Parameters: user_id={user_id}, title={title}, category={category}, target_score={target_score}, target_date={target_date}")
            print("=" * 80)
            # Rollback on error
            db.session.rollback()
            raise
    
    @staticmethod
    def get_user_goals(user_id):
        """
        Get all goals for a user
        """
        return LearningGoal.query.filter_by(user_id=user_id).order_by(LearningGoal.created_at.desc()).all()
    
    @staticmethod
    def get_goal_by_id(goal_id):
        """
        Get goal by ID
        """
        return LearningGoal.query.get(goal_id)
    
    @staticmethod
    def update_goal(goal_id, title=None, category=None, target_score=None, current_score=None, status=None, target_date=None):
        """
        Update a goal
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            if title is not None:
                title_str = str(title).strip()
                goal.title = title_str
                goal.goal_name = title_str  # Keep goal_name in sync with title
            if category is not None:
                goal.category = category
            if target_score is not None:
                goal.target_score = target_score
            if current_score is not None:
                goal.current_score = current_score
            if status is not None:
                goal.status = status
            if target_date is not None:
                goal.target_date = target_date
            goal.updated_at = datetime.utcnow()
            db.session.commit()
            return goal
        return None
    
    @staticmethod
    def mark_as_completed(goal_id):
        """
        Mark a goal as completed
        """
        goal = LearningGoal.query.get(goal_id)
        if goal:
            goal.status = 'Completed'
            goal.updated_at = datetime.utcnow()
            db.session.commit()
            return goal
        return None
    
    @staticmethod
    def get_goals_summary(user_id):
        """
        Get summary statistics for user goals
        Returns: dict with active_count, completed_count, average_progress
        """
        all_goals = LearningGoal.query.filter_by(user_id=user_id).all()
        active_goals = [g for g in all_goals if g.status == 'In Progress']
        completed_goals = [g for g in all_goals if g.status == 'Completed']
        
        # Calculate average progress
        if active_goals:
            total_progress = 0
            for goal in active_goals:
                target = goal.target_score if goal.target_score > 0 else 100
                progress = (goal.current_score / target) * 100 if target > 0 else 0
                total_progress += min(progress, 100)
            average_progress = total_progress / len(active_goals)
        else:
            average_progress = 0
        
        return {
            'active_count': len(active_goals),
            'completed_count': len(completed_goals),
            'average_progress': round(average_progress, 1)
        }
    
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
    
    @staticmethod
    def update_goal_progress(user_id, category):
        """
        Automatically update goal progress based on latest assessment results
        This is called whenever a new quiz result, writing submission, or speaking submission is recorded
        
        Args:
            user_id: ID of the user
            category: Category to update (Writing, Speaking, Quiz)
        """
        # Get all active goals for this user in the specified category
        goals = LearningGoal.query.filter_by(
            user_id=user_id,
            category=category,
            status='In Progress'
        ).all()
        
        if not goals:
            return
        
        # Calculate current average score based on category
        current_score = 0.0
        
        if category == 'Quiz':
            # Get average quiz score
            quizzes = Quiz.query.filter_by(user_id=user_id).all()
            if quizzes:
                current_score = sum(q.score for q in quizzes) / len(quizzes)
        
        elif category == 'Writing':
            # Get average writing submission score
            writing_subs = Submission.query.filter_by(
                student_id=user_id,
                submission_type='WRITING'
            ).join(Grade).all()
            if writing_subs:
                current_score = sum(s.grade.score for s in writing_subs) / len(writing_subs)
        
        elif category == 'Speaking':
            # Get average speaking submission score
            speaking_subs = Submission.query.filter_by(
                student_id=user_id,
                submission_type='SPEAKING'
            ).join(Grade).all()
            if speaking_subs:
                current_score = sum(s.grade.score for s in speaking_subs) / len(speaking_subs)
        
        # Update all goals in this category
        for goal in goals:
            goal.current_score = current_score
            
            # Check if goal is completed
            if current_score >= goal.target_score:
                goal.status = 'Completed'
            
            # Always update the updated_at timestamp when progress changes
            goal.updated_at = datetime.utcnow()
        
        db.session.commit()
        return goals

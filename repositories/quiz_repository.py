from models.entities import Question, Quiz
from models.database import db

class QuizRepository:
    @staticmethod
    def fetch_questions_from_db(limit=5, category=None):
        """
        Fetch questions from database
        """
        query = Question.query
        if category:
            query = query.filter_by(category=category)
        return query.limit(limit).all()
    
    @staticmethod
    def save_result(user_id, quiz_title, score):
        """
        Save quiz result to database
        """
        new_quiz = Quiz(
            user_id=user_id,
            quiz_title=quiz_title,
            score=score
        )
        db.session.add(new_quiz)
        db.session.commit()
        return new_quiz
    
    @staticmethod
    def get_quizzes(user_id=None):
        """
        Get quizzes, optionally filtered by user_id
        """
        query = Quiz.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(Quiz.date_taken.desc()).all()







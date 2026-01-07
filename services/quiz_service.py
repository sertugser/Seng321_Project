from models.entities import Question, Quiz
from models.database import db

class QuizService:
    @staticmethod
    def get_questions(limit=5, category=None):
        """
        Get questions from database
        """
        query = Question.query
        if category:
            query = query.filter_by(category=category)
        return query.limit(limit).all()
    
    @staticmethod
    def check_answer(question_id, user_answer):
        """
        Check if user answer is correct
        Returns True if correct, False otherwise
        """
        question = Question.query.get(question_id)
        if not question:
            return False
        
        return user_answer.upper() == question.correct_answer.upper()
    
    @staticmethod
    def calculate_final_score(question_ids, user_answers):
        """
        Calculate final score based on correct answers
        Returns (correct_count, total_count, percentage_score)
        """
        correct = 0
        total = len(question_ids)
        
        for q_id in question_ids:
            if q_id in user_answers:
                question = Question.query.get(q_id)
                if question and user_answers[q_id].upper() == question.correct_answer.upper():
                    correct += 1
        
        score = round((correct / total) * 100, 1) if total > 0 else 0
        return (correct, total, score)
    
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







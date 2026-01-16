from models.entities import Question, Quiz, QuizDetail
from models.database import db
from sqlalchemy import func

class QuizService:
    @staticmethod
    def get_questions(limit=5, category=None):
        """
        Get questions from database with case-insensitive category matching
        """
        query = Question.query
        
        if category:
            # Case-insensitive category matching
            # Normalize category to lowercase for comparison
            category_lower = category.lower() if category else None
            query = query.filter(func.lower(Question.category) == category_lower)
        
        questions = query.limit(limit).all()
        
        # If no questions found and category was specified, try to find any questions
        if not questions and category:
            # Check if any questions exist at all
            total_questions = Question.query.count()
            if total_questions == 0:
                # Database is empty - questions need to be seeded
                return []
            # Questions exist but not for this category
            return []
        
        return questions
    
    @staticmethod
    def check_questions_available(category=None):
        """
        Check if questions are available for a given category
        Returns (available: bool, message: str)
        """
        total_count = Question.query.count()
        
        if total_count == 0:
            return False, "No questions available in the database. Please contact your administrator to add questions."
        
        if category:
            category_lower = category.lower()
            category_count = Question.query.filter(func.lower(Question.category) == category_lower).count()
            if category_count == 0:
                available_categories = db.session.query(Question.category.distinct()).all()
                categories = [cat[0] for cat in available_categories if cat[0]]
                return False, f"No questions available for '{category}' category. Available categories: {', '.join(categories) if categories else 'None'}"
        
        return True, "Questions available"
    
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
            key = str(q_id)
            if key in user_answers:
                question = Question.query.get(q_id)
                if question and user_answers[key].upper() == question.correct_answer.upper():
                    correct += 1
        
        score = round((correct / total) * 100, 1) if total > 0 else 0
        return (correct, total, score)
    
    @staticmethod
    def save_result(user_id, quiz_title, score, details=None, category=None):
        """
        Save quiz result to database
        Args:
            user_id: ID of the user who took the quiz
            quiz_title: Title of the quiz
            score: Final score percentage
            details: Optional list of question details
            category: Optional quiz category (grammar, vocabulary, reading, mixed)
        """
        new_quiz = Quiz(
            user_id=user_id,
            quiz_title=quiz_title,
            score=score,
            category=category  # Save the category
        )
        db.session.add(new_quiz)
        db.session.flush()  # get new_quiz.id without full commit

        # Optionally save per-question details
        if details:
            for item in details:
                detail = QuizDetail(
                    quiz_id=new_quiz.id,
                    question_text=item.get('question_text', ''),
                    user_answer=item.get('user_answer'),
                    correct_answer=item.get('correct_answer'),
                    is_correct=item.get('is_correct', False),
                    explanation=item.get('explanation')  # Save AI-generated explanation
                )
                db.session.add(detail)

        db.session.commit()
        return new_quiz







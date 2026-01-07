from models.entities import Grade, Submission
from models.database import db

class GradingService:
    @staticmethod
    def calculate_score(grammar_errors, vocabulary_errors):
        """
        Simple scoring: start with 100, deduct points for errors
        """
        base_score = 100
        grammar_deduction = len(grammar_errors) * 5 if grammar_errors else 0
        vocab_deduction = len(vocabulary_errors) * 3 if vocabulary_errors else 0
        
        final_score = base_score - grammar_deduction - vocab_deduction
        return max(0, min(100, final_score))  # Keep between 0 and 100
    
    @staticmethod
    def process_evaluation(submission_id, ai_result):
        """
        Process AI evaluation result and save grade
        """
        submission = Submission.query.get(submission_id)
        if not submission:
            return False
        
        # Calculate score from AI result
        grammar_errors = ai_result.get('grammar_errors', [])
        vocab_suggestions = ai_result.get('vocabulary_suggestions', [])
        
        # Use AI score if available, otherwise calculate
        if ai_result.get('score') is not None:
            score = ai_result.get('score')
        else:
            score = GradingService.calculate_score(grammar_errors, vocab_suggestions)
        
        # Convert lists to text
        grammar_text = "\n".join(grammar_errors) if grammar_errors else None
        vocab_text = "\n".join(vocab_suggestions) if vocab_suggestions else None
        
        # Create or update grade
        if submission.grade:
            submission.grade.score = score
            submission.grade.general_feedback = ai_result.get('general_feedback', '')
            submission.grade.grammar_feedback = grammar_text
            submission.grade.vocabulary_feedback = vocab_text
        else:
            new_grade = Grade(
                submission_id=submission_id,
                score=score,
                general_feedback=ai_result.get('general_feedback', ''),
                grammar_feedback=grammar_text,
                vocabulary_feedback=vocab_text
            )
            db.session.add(new_grade)
        
        db.session.commit()
        return True
    
    @staticmethod
    def update_student_grade(submission_id, new_score, new_feedback=None):
        """
        Update grade manually (for instructors)
        """
        submission = Submission.query.get(submission_id)
        if not submission or not submission.grade:
            return False
        
        submission.grade.score = new_score
        if new_feedback:
            submission.grade.general_feedback = new_feedback
        
        db.session.commit()
        return True







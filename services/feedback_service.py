from models.entities import Submission, Grade
from models.database import db

class FeedbackService:
    @staticmethod
    def fetch_results(submission_id):
        """
        Fetch feedback results for a submission
        """
        submission = Submission.query.get(submission_id)
        if not submission:
            return None
        
        return {
            'submission': submission,
            'grade': submission.grade,
            'grammar_feedback': submission.grade.grammar_feedback if submission.grade else None,
            'vocabulary_feedback': submission.grade.vocabulary_feedback if submission.grade else None,
            'general_feedback': submission.grade.general_feedback if submission.grade else None,
            'score': submission.grade.score if submission.grade else None
        }
    
    @staticmethod
    def get_feedback_by_submission_id(submission_id):
        """
        Get feedback by submission ID (alias for fetch_results)
        """
        return FeedbackService.fetch_results(submission_id)
    
    @staticmethod
    def save_evaluation(submission_id, score, grammar_feedback=None, vocabulary_feedback=None, general_feedback=None):
        """
        Save evaluation/feedback for a submission
        """
        submission = Submission.query.get(submission_id)
        if not submission:
            return False
        
        if submission.grade:
            submission.grade.score = score
            if grammar_feedback:
                submission.grade.grammar_feedback = grammar_feedback
            if vocabulary_feedback:
                submission.grade.vocabulary_feedback = vocabulary_feedback
            if general_feedback:
                submission.grade.general_feedback = general_feedback
        else:
            new_grade = Grade(
                submission_id=submission_id,
                score=score,
                grammar_feedback=grammar_feedback,
                vocabulary_feedback=vocabulary_feedback,
                general_feedback=general_feedback
            )
            db.session.add(new_grade)
        
        db.session.commit()
        return True







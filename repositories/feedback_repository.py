from models.entities import Submission, Grade
from models.database import db

class FeedbackRepository:
    @staticmethod
    def find_feedback_by_submission_id(submission_id):
        """
        Find feedback by submission ID
        """
        submission = Submission.query.get(submission_id)
        if submission and submission.grade:
            return submission.grade
        return None
    
    @staticmethod
    def save_evaluation(submission_id, score, grammar_feedback=None, vocabulary_feedback=None, general_feedback=None):
        """
        Save evaluation/feedback for a submission
        """
        submission = Submission.query.get(submission_id)
        if not submission:
            return None
        
        if submission.grade:
            # Update existing grade
            submission.grade.score = score
            if grammar_feedback:
                submission.grade.grammar_feedback = grammar_feedback
            if vocabulary_feedback:
                submission.grade.vocabulary_feedback = vocabulary_feedback
            if general_feedback:
                submission.grade.general_feedback = general_feedback
        else:
            # Create new grade
            new_grade = Grade(
                submission_id=submission_id,
                score=score,
                grammar_feedback=grammar_feedback,
                vocabulary_feedback=vocabulary_feedback,
                general_feedback=general_feedback
            )
            db.session.add(new_grade)
        
        db.session.commit()
        return submission.grade if submission.grade else new_grade







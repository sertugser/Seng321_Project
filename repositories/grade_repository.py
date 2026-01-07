from models.entities import Grade, Submission
from models.database import db

class GradeRepository:
    @staticmethod
    def update_student_grade(submission_id, score, feedback=None, grammar_feedback=None, vocabulary_feedback=None):
        """
        Update or create student grade
        """
        submission = Submission.query.get(submission_id)
        if not submission:
            return None
        
        if submission.grade:
            # Update existing grade
            submission.grade.score = score
            if feedback is not None:
                submission.grade.general_feedback = feedback
            if grammar_feedback is not None:
                submission.grade.grammar_feedback = grammar_feedback
            if vocabulary_feedback is not None:
                submission.grade.vocabulary_feedback = vocabulary_feedback
        else:
            # Create new grade
            new_grade = Grade(
                submission_id=submission_id,
                score=score,
                general_feedback=feedback or '',
                grammar_feedback=grammar_feedback,
                vocabulary_feedback=vocabulary_feedback
            )
            db.session.add(new_grade)
        
        db.session.commit()
        return submission.grade if submission.grade else new_grade
    
    @staticmethod
    def fetch_all_grades(student_id=None):
        """
        Fetch all grades, optionally filtered by student_id
        """
        if student_id:
            submissions = Submission.query.filter_by(student_id=student_id).all()
            return [s.grade for s in submissions if s.grade]
        else:
            return Grade.query.all()







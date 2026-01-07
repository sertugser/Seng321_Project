from models.entities import Submission, Grade
from models.database import db

class SubmissionRepository:
    @staticmethod
    def save_submission(student_id, file_path, submission_type, text_content=None):
        new_submission = Submission(
            student_id=student_id,
            type=submission_type,
            file_path=file_path,
            text_content=text_content
        )
        db.session.add(new_submission)
        db.session.commit()
        return new_submission

    @staticmethod
    def update_grade(submission_id, score, grammar_fb, vocab_fb):
       
        submission = Submission.query.get(submission_id)
        if submission:
           
            new_grade = Grade(
                submission_id=submission_id,
                score=score,
                grammar_feedback=grammar_fb,
                vocabulary_feedback=vocab_fb
            )
            db.session.add(new_grade)
            db.session.commit()
            return new_grade
        return None
    
    @staticmethod
    def get_student_submissions(student_id):
        return Submission.query.filter_by(student_id=student_id).all()
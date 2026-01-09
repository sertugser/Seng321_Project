from models.entities import Submission
from models.database import db
from werkzeug.utils import secure_filename
import os

class SubmissionService:
    @staticmethod
    def validate_file_format(filename, submission_type=None):
        """
        Validate if file format is supported
        Returns True if valid, False otherwise
        """
        if not filename:
            return False
        
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Audio formats for speaking submissions
        if submission_type == 'SPEAKING':
            allowed_extensions = ['.mp3', '.wav', '.m4a', '.ogg']
            return file_ext in allowed_extensions
        
        # Default: writing/handwritten formats
        allowed_extensions = ['.docx', '.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif']
        return file_ext in allowed_extensions
    
    @staticmethod
    def process_submission(file, upload_folder, student_id, activity_id, submission_type, text_content=None):
        """
        Process submission: validate, save file, create submission record
        Returns submission object or None if failed
        """
        if not file or not file.filename:
            return None
        
        # Validate file format
        if not SubmissionService.validate_file_format(file.filename):
            return None
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        os.makedirs(upload_folder, exist_ok=True)
        file.save(file_path)
        
        # Create submission
        new_submission = Submission(
            student_id=student_id,
            activity_id=activity_id,
            submission_type=submission_type,
            file_path=filename,
            text_content=text_content
        )
        db.session.add(new_submission)
        db.session.commit()
        
        return new_submission
    
    @staticmethod
    def save_submission_text(student_id, activity_id, submission_type, text_content, file_path=None):
        """
        Save text-based submission (no file upload)
        """
        new_submission = Submission(
            student_id=student_id,
            activity_id=activity_id,
            submission_type=submission_type,
            file_path=file_path,
            text_content=text_content
        )
        db.session.add(new_submission)
        db.session.commit()
        
        return new_submission


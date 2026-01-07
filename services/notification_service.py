from flask import flash
from models.entities import User

class NotificationService:
    @staticmethod
    def send_notification(user_id, message, notification_type='info'):
        """
        Send notification to user
        For now, uses flash messages. Can be extended with email/database notifications
        """
        # In a real system, this would send email, push notification, or save to database
        # For now, we'll just use flash messages which are already in the system
        flash(message, notification_type)
        return True
    
    @staticmethod
    def notify_grade_ready(student_id, submission_id):
        """
        Notify student that their grade is ready
        """
        user = User.query.get(student_id)
        if user:
            message = f"Your submission has been graded! Check your feedback."
            NotificationService.send_notification(student_id, message, 'success')
            return True
        return False







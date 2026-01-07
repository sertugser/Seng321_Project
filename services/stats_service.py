from models.entities import Submission, Grade, Quiz
from models.database import db
from datetime import datetime, timedelta
from collections import defaultdict

class StatsService:
    @staticmethod
    def get_dashboard_data(student_id):
        """
        Get dashboard data for a student
        Returns dictionary with scores, progress, etc.
        """
        submissions = Submission.query.filter_by(student_id=student_id).all()
        
        # Calculate scores
        speaking_subs = [s for s in submissions if s.submission_type == 'SPEAKING' and s.grade]
        writing_subs = [s for s in submissions if s.submission_type == 'WRITING' and s.grade]
        handwritten_subs = [s for s in submissions if s.submission_type == 'HANDWRITTEN' and s.grade]
        
        speaking_score = 0.0
        if speaking_subs:
            scores = []
            for sub in speaking_subs:
                if sub.grade.pronunciation_score and sub.grade.fluency_score:
                    scores.append((sub.grade.pronunciation_score + sub.grade.fluency_score) / 2)
            speaking_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        
        writing_score = round(sum(s.grade.score for s in writing_subs) / len(writing_subs), 1) if writing_subs else 0.0
        handwritten_score = round(sum(s.grade.score for s in handwritten_subs) / len(handwritten_subs), 1) if handwritten_subs else 0.0
        
        # Get quiz data
        quizzes = Quiz.query.filter_by(user_id=student_id).all()
        quiz_score = 0.0
        if quizzes:
            quiz_scores_list = [q.score for q in quizzes if q.score is not None]
            quiz_score = round(sum(quiz_scores_list) / len(quiz_scores_list), 1) if quiz_scores_list else 0.0
        
        return {
            'speaking_score': speaking_score,
            'writing_score': writing_score,
            'handwritten_score': handwritten_score,
            'quiz_score': quiz_score,
            'total_submissions': len(submissions),
            'completed_quizzes': len(quizzes)
        }
    
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
    
    @staticmethod
    def fetch_recommendations(student_id):
        """
        Fetch recommendations based on student performance
        Simple implementation - can be enhanced with AI
        """
        data = StatsService.get_dashboard_data(student_id)
        recommendations = []
        
        if data['speaking_score'] < 70:
            recommendations.append("Focus on improving your speaking skills")
        if data['writing_score'] < 70:
            recommendations.append("Practice more writing exercises")
        if data['quiz_score'] < 70:
            recommendations.append("Take more quizzes to improve")
        
        return recommendations
    
    @staticmethod
    def consolidate_view_data(student_id):
        """
        Consolidate all view data for dashboard
        """
        dashboard_data = StatsService.get_dashboard_data(student_id)
        recommendations = StatsService.fetch_recommendations(student_id)
        
        return {
            **dashboard_data,
            'recommendations': recommendations
        }







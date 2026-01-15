"""
Adaptive Insights Service (UC17)
Provides AI-powered adaptive learning insights and recommendations
"""
from datetime import datetime, timedelta
from models.entities import User, Submission, Grade, Quiz, LearningGoal, AdaptiveInsight
from models.database import db
from services.ai_service import AIService
from services.stats_service import StatsService

class AdaptiveInsightsService:
    """
    Service for generating adaptive learning insights using AI analysis
    Periodically analyzes student performance and provides personalized recommendations
    """
    
    @staticmethod
    def generate_insights_for_student(student_id):
        """
        Generate adaptive insights for a specific student
        Analyzes performance patterns and provides AI-powered recommendations
        """
        student = User.query.get(student_id)
        if not student or student.role != 'Student':
            return {'success': False, 'message': 'Invalid student ID'}
        
        try:
            # Get performance data
            performance_data = StatsService.get_dashboard_data(student_id)
            
            # Get recent submissions
            recent_submissions = Submission.query.filter_by(student_id=student_id)\
                .order_by(Submission.created_at.desc()).limit(20).all()
            
            # Get learning goals
            goals = LearningGoal.query.filter_by(user_id=student_id).all()
            
            # Analyze performance patterns
            insights = []
            
            # 1. Performance-based recommendations
            perf_insight = AdaptiveInsightsService._analyze_performance_patterns(
                student_id, performance_data, recent_submissions
            )
            if perf_insight:
                insights.append(perf_insight)
            
            # 2. Goal progress insights
            goal_insight = AdaptiveInsightsService._analyze_goal_progress(
                student_id, goals, performance_data
            )
            if goal_insight:
                insights.append(goal_insight)
            
            # 3. Learning path recommendations (AI-powered)
            learning_path_insight = AdaptiveInsightsService._generate_learning_path(
                student_id, performance_data, recent_submissions
            )
            if learning_path_insight:
                insights.append(learning_path_insight)
            
            # 4. Weak area predictions
            prediction_insight = AdaptiveInsightsService._predict_weak_areas(
                student_id, performance_data, recent_submissions
            )
            if prediction_insight:
                insights.append(prediction_insight)
            
            # Save insights to database
            for insight_data in insights:
                insight = AdaptiveInsight(
                    user_id=student_id,
                    insight_type=insight_data['type'],
                    insight_text=insight_data['text'],
                    area_focus=insight_data.get('area'),
                    confidence_score=insight_data.get('confidence', 0.7),
                    recommendation_action=insight_data.get('action'),
                    is_active=True,
                    generated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)  # Insights expire after 7 days
                )
                db.session.add(insight)
            
            db.session.commit()
            
            return {
                'success': True,
                'insights_generated': len(insights),
                'insights': insights
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error generating insights: {str(e)}'}
    
    @staticmethod
    def _analyze_performance_patterns(student_id, performance_data, recent_submissions):
        """Analyze performance patterns and identify trends"""
        if not recent_submissions or len(recent_submissions) < 3:
            return None
        
        # Calculate trend (improving/declining)
        recent_scores = []
        for sub in recent_submissions[:10]:
            if sub.grade and sub.grade.instructor_approved:
                recent_scores.append(sub.grade.score)
        
        if len(recent_scores) < 3:
            return None
        
        # Simple trend analysis
        first_half_avg = sum(recent_scores[:len(recent_scores)//2]) / (len(recent_scores)//2)
        second_half_avg = sum(recent_scores[len(recent_scores)//2:]) / (len(recent_scores) - len(recent_scores)//2)
        
        trend = "improving" if second_half_avg > first_half_avg else "declining" if second_half_avg < first_half_avg else "stable"
        
        # Identify weakest area
        areas = {
            'Speaking': performance_data.get('speaking_score', 0),
            'Writing': performance_data.get('writing_score', 0),
            'Quiz': performance_data.get('quiz_score', 0),
            'Handwritten': performance_data.get('handwritten_score', 0)
        }
        non_zero_areas = {k: v for k, v in areas.items() if v > 0}
        
        if non_zero_areas:
            weakest_area = min(non_zero_areas, key=non_zero_areas.get)
            weakest_score = non_zero_areas[weakest_area]
            
            insight_text = f"Your performance trend is {trend}. "
            if trend == "improving":
                insight_text += f"Great progress! Your {weakest_area} skills ({weakest_score}%) could benefit from additional practice."
            elif trend == "declining":
                insight_text += f"Your scores have decreased recently. Focus on {weakest_area} practice to get back on track."
            else:
                insight_text += f"Keep practicing! Your {weakest_area} area ({weakest_score}%) needs attention."
            
            action = f"Focus on {weakest_area} activities"
            if weakest_area == "Speaking":
                action += " - try recording more speaking assignments"
            elif weakest_area == "Writing":
                action += " - submit more writing exercises"
            elif weakest_area == "Quiz":
                action += " - complete more interactive quizzes"
            elif weakest_area == "Handwritten":
                action += " - practice handwritten submissions"
            
            return {
                'type': 'performance',
                'text': insight_text,
                'area': weakest_area.lower(),
                'confidence': 0.8,
                'action': action
            }
        
        return None
    
    @staticmethod
    def _analyze_goal_progress(student_id, goals, performance_data):
        """Analyze progress towards learning goals"""
        if not goals:
            return None
        
        active_goals = [g for g in goals if g.current_value < g.target_value]
        if not active_goals:
            return None
        
        # Find goal with lowest progress
        progress_ratios = [(g, g.current_value / g.target_value) for g in active_goals]
        lowest_progress_goal = min(progress_ratios, key=lambda x: x[1])[0]
        
        progress_percentage = (lowest_progress_goal.current_value / lowest_progress_goal.target_value) * 100
        
        insight_text = f"Your goal '{lowest_progress_goal.goal_name}' is {progress_percentage:.1f}% complete. "
        
        if progress_percentage < 50:
            insight_text += "You're making steady progress. Keep practicing to reach your target!"
            action = f"Increase practice for {lowest_progress_goal.goal_name}"
        elif progress_percentage < 80:
            insight_text += "You're more than halfway there! A bit more effort will help you achieve your goal."
            action = f"Maintain consistent practice for {lowest_progress_goal.goal_name}"
        else:
            insight_text += "You're almost there! Push a little harder to complete your goal."
            action = f"Final push to complete {lowest_progress_goal.goal_name}"
        
        return {
            'type': 'recommendation',
            'text': insight_text,
            'area': lowest_progress_goal.category.lower() if lowest_progress_goal.category else None,
            'confidence': 0.9,
            'action': action
        }
    
    @staticmethod
    def _generate_learning_path(student_id, performance_data, recent_submissions):
        """Generate AI-powered learning path recommendations"""
        # Use AI to analyze overall performance and suggest learning path
        try:
            # Prepare context for AI
            context = f"""
            Student Performance Summary:
            - Speaking Score: {performance_data.get('speaking_score', 0)}/100
            - Writing Score: {performance_data.get('writing_score', 0)}/100
            - Quiz Score: {performance_data.get('quiz_score', 0)}/100
            - Handwritten Score: {performance_data.get('handwritten_score', 0)}/100
            - Total Submissions: {performance_data.get('total_submissions', 0)}
            - Completed Quizzes: {performance_data.get('completed_quizzes', 0)}
            
            Recent Activity: {len(recent_submissions)} recent submissions
            """
            
            # Get AI recommendation (simplified - in production, use full AI analysis)
            # For now, use rule-based recommendations enhanced with AI service availability
            
            # Determine recommended next steps
            speaking_score = performance_data.get('speaking_score', 0)
            writing_score = performance_data.get('writing_score', 0)
            quiz_score = performance_data.get('quiz_score', 0)
            
            if speaking_score < 70:
                insight_text = "Your speaking skills need improvement. Practice pronunciation and fluency regularly."
                action = "Complete speaking assignments daily"
                area = "speaking"
            elif writing_score < 70:
                insight_text = "Focus on improving your writing skills. Pay attention to grammar and vocabulary feedback."
                action = "Submit more writing exercises"
                area = "writing"
            elif quiz_score < 70:
                insight_text = "Take more interactive quizzes to strengthen your understanding of key concepts."
                action = "Complete quiz activities"
                area = "quiz"
            else:
                insight_text = "You're performing well across all areas! Continue practicing to maintain and improve your skills."
                action = "Maintain consistent practice schedule"
                area = None
            
            return {
                'type': 'recommendation',
                'text': insight_text,
                'area': area,
                'confidence': 0.75,
                'action': action
            }
        except Exception as e:
            return None
    
    @staticmethod
    def _predict_weak_areas(student_id, performance_data, recent_submissions):
        """Predict areas where student might struggle"""
        # Analyze patterns to predict potential weak areas
        if not recent_submissions or len(recent_submissions) < 5:
            return None
        
        # Count errors by type from recent submissions
        error_types = {'grammar': 0, 'vocabulary': 0, 'pronunciation': 0, 'fluency': 0}
        
        for sub in recent_submissions[:10]:
            if sub.grade:
                if sub.grade.grammar_feedback:
                    error_types['grammar'] += len(sub.grade.grammar_feedback.split('\n'))
                if sub.grade.vocabulary_feedback:
                    error_types['vocabulary'] += len(sub.grade.vocabulary_feedback.split('\n'))
                if sub.grade.pronunciation_score and sub.grade.pronunciation_score < 80:
                    error_types['pronunciation'] += 1
                if sub.grade.fluency_score and sub.grade.fluency_score < 80:
                    error_types['fluency'] += 1
        
        # Find most common issue
        if max(error_types.values()) > 0:
            most_common_issue = max(error_types, key=error_types.get)
            
            predictions = {
                'grammar': "You may struggle with grammar in future assignments. Focus on reviewing grammar rules.",
                'vocabulary': "Vocabulary is a potential challenge area. Expand your vocabulary through reading and practice.",
                'pronunciation': "Pronunciation needs attention. Practice difficult words and listen to native speakers.",
                'fluency': "Fluency improvement is needed. Practice speaking without pauses and work on smooth transitions."
            }
            
            actions = {
                'grammar': "Review grammar lessons and practice exercises",
                'vocabulary': "Read more and practice using new words",
                'pronunciation': "Record yourself and compare with native speakers",
                'fluency': "Practice speaking exercises daily"
            }
            
            return {
                'type': 'prediction',
                'text': predictions.get(most_common_issue, "Continue practicing all areas."),
                'area': most_common_issue,
                'confidence': 0.7,
                'action': actions.get(most_common_issue, "Continue practicing")
            }
        
        return None
    
    @staticmethod
    def get_active_insights(student_id):
        """Get active insights for a student"""
        now = datetime.utcnow()
        return AdaptiveInsight.query.filter(
            AdaptiveInsight.user_id == student_id,
            AdaptiveInsight.is_active == True,
            db.or_(
                AdaptiveInsight.expires_at.is_(None),
                AdaptiveInsight.expires_at > now
            )
        ).order_by(AdaptiveInsight.generated_at.desc()).all()
    
    @staticmethod
    def generate_insights_for_all_students():
        """Generate insights for all students (for periodic batch processing)"""
        students = User.query.filter_by(role='Student').all()
        results = []
        
        for student in students:
            result = AdaptiveInsightsService.generate_insights_for_student(student.id)
            results.append({
                'student_id': student.id,
                'student_name': student.username,
                'success': result.get('success', False),
                'insights_generated': result.get('insights_generated', 0)
            })
        
        return {
            'total_students': len(students),
            'success_count': sum(1 for r in results if r['success']),
            'total_insights': sum(r['insights_generated'] for r in results),
            'details': results
        }

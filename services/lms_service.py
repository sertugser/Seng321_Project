import requests
import json
from datetime import datetime
from models.entities import LMSIntegration, Grade, Submission, User
from models.database import db

class LMSService:
    """
    LMS Integration Service for Canvas, Moodle, and Blackboard
    Provides grade synchronization functionality
    """
    
    @staticmethod
    def get_active_integrations():
        """Get all active LMS integrations"""
        return LMSIntegration.query.filter_by(is_active=True, sync_enabled=True).all()
    
    @staticmethod
    def sync_grades_to_lms(lms_integration_id, student_id=None, submission_id=None):
        """
        Sync grades to external LMS
        Args:
            lms_integration_id: ID of LMS integration
            student_id: Optional - sync all grades for a specific student
            submission_id: Optional - sync a specific submission
        """
        lms = LMSIntegration.query.get(lms_integration_id)
        if not lms or not lms.is_active or not lms.sync_enabled:
            return {'success': False, 'message': 'LMS integration not active or sync disabled'}
        
        try:
            if submission_id:
                # Sync single submission
                submission = Submission.query.get(submission_id)
                if not submission or not submission.grade or not submission.grade.instructor_approved:
                    return {'success': False, 'message': 'Submission not found or not graded'}
                
                result = LMSService._sync_single_grade(lms, submission)
                return result
            elif student_id:
                # Sync all approved grades for a student
                submissions = Submission.query.filter_by(student_id=student_id).all()
                approved_submissions = [s for s in submissions if s.grade and s.grade.instructor_approved]
                
                results = []
                for submission in approved_submissions:
                    result = LMSService._sync_single_grade(lms, submission)
                    results.append(result)
                
                success_count = sum(1 for r in results if r.get('success'))
                return {
                    'success': success_count > 0,
                    'message': f'Synced {success_count}/{len(approved_submissions)} grades',
                    'details': results
                }
            else:
                return {'success': False, 'message': 'Either student_id or submission_id must be provided'}
        except Exception as e:
            return {'success': False, 'message': f'Error syncing grades: {str(e)}'}
    
    @staticmethod
    def _sync_single_grade(lms, submission):
        """Sync a single grade to LMS"""
        if lms.lms_type == 'canvas':
            return LMSService._sync_to_canvas(lms, submission)
        elif lms.lms_type == 'moodle':
            return LMSService._sync_to_moodle(lms, submission)
        elif lms.lms_type == 'blackboard':
            return LMSService._sync_to_blackboard(lms, submission)
        else:
            return {'success': False, 'message': f'Unsupported LMS type: {lms.lms_type}'}
    
    @staticmethod
    def _sync_to_canvas(lms, submission):
        """Sync grade to Canvas LMS"""
        try:
            # Canvas API: PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id
            student = User.query.get(submission.student_id)
            if not student or not student.email:
                return {'success': False, 'message': 'Student email not found'}
            
            # Get Canvas user ID from email (simplified - in production, use proper API)
            canvas_user_id = LMSService._get_canvas_user_id(lms, student.email)
            if not canvas_user_id:
                return {'success': False, 'message': 'Student not found in Canvas'}
            
            # Get assignment ID (from activity or use default)
            assignment_id = submission.activity_id if submission.activity_id else 'default'
            
            url = f"{lms.api_url}/api/v1/courses/{lms.course_id}/assignments/{assignment_id}/submissions/{canvas_user_id}"
            headers = {
                'Authorization': f'Bearer {lms.api_key}',
                'Content-Type': 'application/json'
            }
            
            grade_data = {
                'submission': {
                    'posted_grade': submission.grade.score
                }
            }
            
            response = requests.put(url, headers=headers, json=grade_data, timeout=10)
            
            if response.status_code in [200, 201]:
                # Update last sync time
                lms.last_sync_at = datetime.utcnow()
                db.session.commit()
                return {'success': True, 'message': 'Grade synced to Canvas successfully'}
            else:
                return {'success': False, 'message': f'Canvas API error: {response.status_code} - {response.text}'}
        except Exception as e:
            return {'success': False, 'message': f'Canvas sync error: {str(e)}'}
    
    @staticmethod
    def _sync_to_moodle(lms, submission):
        """Sync grade to Moodle LMS"""
        try:
            # Moodle Web Services API
            student = User.query.get(submission.student_id)
            if not student or not student.email:
                return {'success': False, 'message': 'Student email not found'}
            
            url = f"{lms.api_url}/webservice/rest/server.php"
            params = {
                'wstoken': lms.api_key,
                'wsfunction': 'core_grades_update_grades',
                'moodlewsrestformat': 'json',
                'source': 'external',
                'courseid': lms.course_id,
                'component': 'mod_assign',
                'activityid': submission.activity_id if submission.activity_id else 0,
                'itemnumber': 0,
                'grades[0][studentid]': LMSService._get_moodle_user_id(lms, student.email),
                'grades[0][grade]': submission.grade.score
            }
            
            response = requests.post(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('warnings'):
                    return {'success': False, 'message': f'Moodle API warning: {result["warnings"]}'}
                
                lms.last_sync_at = datetime.utcnow()
                db.session.commit()
                return {'success': True, 'message': 'Grade synced to Moodle successfully'}
            else:
                return {'success': False, 'message': f'Moodle API error: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Moodle sync error: {str(e)}'}
    
    @staticmethod
    def _sync_to_blackboard(lms, submission):
        """Sync grade to Blackboard LMS"""
        try:
            # Blackboard Learn REST API
            student = User.query.get(submission.student_id)
            if not student or not student.email:
                return {'success': False, 'message': 'Student email not found'}
            
            # Get Blackboard user ID
            bb_user_id = LMSService._get_blackboard_user_id(lms, student.email)
            if not bb_user_id:
                return {'success': False, 'message': 'Student not found in Blackboard'}
            
            # Blackboard grade column endpoint
            url = f"{lms.api_url}/learn/api/public/v1/courses/{lms.course_id}/gradebook/columns/{submission.activity_id or 'default'}/users/{bb_user_id}"
            headers = {
                'Authorization': f'Bearer {lms.api_key}',
                'Content-Type': 'application/json'
            }
            
            grade_data = {
                'score': submission.grade.score,
                'notes': submission.grade.general_feedback or ''
            }
            
            response = requests.patch(url, headers=headers, json=grade_data, timeout=10)
            
            if response.status_code in [200, 201, 204]:
                lms.last_sync_at = datetime.utcnow()
                db.session.commit()
                return {'success': True, 'message': 'Grade synced to Blackboard successfully'}
            else:
                return {'success': False, 'message': f'Blackboard API error: {response.status_code} - {response.text}'}
        except Exception as e:
            return {'success': False, 'message': f'Blackboard sync error: {str(e)}'}
    
    @staticmethod
    def _get_canvas_user_id(lms, email):
        """Get Canvas user ID from email (simplified - uses API)"""
        try:
            url = f"{lms.api_url}/api/v1/courses/{lms.course_id}/users"
            headers = {'Authorization': f'Bearer {lms.api_key}'}
            params = {'search_term': email}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                users = response.json()
                for user in users:
                    if user.get('email') == email:
                        return str(user['id'])
            return None
        except:
            return None
    
    @staticmethod
    def _get_moodle_user_id(lms, email):
        """Get Moodle user ID from email"""
        try:
            url = f"{lms.api_url}/webservice/rest/server.php"
            params = {
                'wstoken': lms.api_key,
                'wsfunction': 'core_user_get_users_by_field',
                'moodlewsrestformat': 'json',
                'field': 'email',
                'values[0]': email
            }
            
            response = requests.post(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    return str(result[0]['id'])
            return None
        except:
            return None
    
    @staticmethod
    def _get_blackboard_user_id(lms, email):
        """Get Blackboard user ID from email"""
        try:
            url = f"{lms.api_url}/learn/api/public/v1/users"
            headers = {'Authorization': f'Bearer {lms.api_key}'}
            params = {'userName': email}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                users = response.json().get('results', [])
                for user in users:
                    if user.get('userName') == email or user.get('contact', {}).get('email') == email:
                        return user['id']
            return None
        except:
            return None

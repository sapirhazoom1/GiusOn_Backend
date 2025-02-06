# controllers/hr_controller.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.hr_service import HRService
from models import User
from datetime import datetime, date, timedelta

hr_bp = Blueprint('hr', __name__)


@hr_bp.route('/hr', methods=['POST'])
def create_hr():
    """Create a new HR user"""
    try:
        data = request.get_json()
        hr = HRService.create_hr_user(data)
        return jsonify({
            'message': 'HR user created successfully',
            'hr_id': hr.id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@hr_bp.route('/volunteers', methods=['POST'])
@jwt_required()
def create_volunteer():
    """Create a new volunteer user"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        volunteer, error = HRService.create_volunteer(data)

        if error:
            return jsonify({'error': error}), 400

        if not volunteer:
            return jsonify({'error': 'Failed to create volunteer'}), 400

        return jsonify({
            'message': 'Volunteer created successfully',
            'user_id': volunteer.user_id,
            'volunteer_id': volunteer.id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def calculate_age(born):
    today = date.today()
    try:
        birthday = born.replace(year=today.year)
    except ValueError: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year

@hr_bp.route('/volunteers', methods=['GET'])
@jwt_required()
def get_volunteers():
    """Get all volunteers"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    volunteers = HRService.get_all_volunteers()
    # return jsonify([{
    #     'id': v.id,
    #     'full_name': v.full_name,
    #     'email': v.user.email,
    #     'phone': v.phone,
    #     'education': v.education,
    #     'primary_profession': v.primary_profession
    # } for v in volunteers]), 200
    payload = [{
        'id': v.id,
        'fullName': v.full_name,
        'idNumber': v.national_id,  # Assuming national_id is the same as idNumber
        'dateOfBirth': v.date_of_birth.strftime('%Y-%m-%d') if v.date_of_birth else None,  # Format dateOfBirth
        'age': calculate_age(v.date_of_birth) if v.date_of_birth else None,  # Function to calculate age (optional)
        'gender': v.gender.value if v.gender else None,  # Handle potential null values
        'profile': v.profile,
        'phone': v.user.phone,
        'email': v.user.email,
        'address': v.address,
        'experience': v.experience,
        'education': v.education,
        'courses': v.courses,
        'languages': v.languages,  # Function to extract languages (optional)
        'interests': v.interests,
        'personalSummary': v.personal_summary,
        'jobStatuses': {str(job_app.job_id): job_app.status.value
                         for job_app in v.applications},  # Map job application status
        'imageUrl': v.user.image_url if v.user.image_url else None  # Handle potential null values
    } for v in volunteers]

    return jsonify(payload), 200

@hr_bp.route('/volunteers/<int:volunteer_id>', methods=['GET'])
@jwt_required()
def get_volunteer(volunteer_id):
    """Get specific volunteer details"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    volunteer = HRService.get_volunteer_by_id(volunteer_id)
    payload = {
        'id': volunteer.id,
        'fullName': volunteer.full_name,
        'idNumber': volunteer.national_id,  # Assuming national_id is the same as idNumber
        'dateOfBirth': volunteer.date_of_birth.strftime('%Y-%m-%d') if volunteer.date_of_birth else None,
        # Format dateOfBirth
        'age': calculate_age(volunteer.date_of_birth) if volunteer.date_of_birth else None,
        # Function to calculate age (optional)
        'gender': volunteer.gender.value if volunteer.gender else None,  # Handle potential null values
        'profile': volunteer.profile,
        'phone': volunteer.user.phone,
        'email': volunteer.user.email,
        'address': volunteer.address,
        'experience': volunteer.experience,
        'education': volunteer.education,
        'courses': volunteer.courses,
        'languages': volunteer.languages,  # Function to extract languages (optional)
        'interests': volunteer.interests,
        'personalSummary': volunteer.personal_summary,
        'jobStatuses': {str(job_app.job_id): job_app.status.value
                        for job_app in volunteer.applications},  # Map job application status
        'imageUrl': volunteer.user.image_url if volunteer.user.image_url else None  # Handle potential null values
    }

    return jsonify(payload), 200


@hr_bp.route('/jobs', methods=['GET'])
@jwt_required()
def get_jobs():
    """Get all jobs"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    jobs = HRService.get_all_jobs()
    payload = [{
        'id': str(job.id),
        'jobName': job.title,
        'jobCategory': job.category,
        'unit': job.unit,
        'address': job.address,
        'positions': job.vacant_positions,
        'openBase': job.is_open_base,
        'closedBase': not job.is_open_base,
        'jobDescription': job.description,
        'additionalInfo': job.additional_info,
        'commonQuestions': job.common_questions,
        'commonAnswers': job.common_answers,
        'education': job.education,
        'techSkills': job.tech_skills,
        'workExperience': job.experience,
        'passedCourses': job.passed_courses,
        'candidateCount': len(job.applications),
        'status': job.status.name,
        'department':job.commander.department if job.commander else None,   # Get department from job
        'commanderId': job.commander_id,
        'applications_count': len(job.applications)
    } for job in jobs]

    return jsonify(payload), 200


@hr_bp.route('/assignments', methods=['POST'])
@jwt_required()
def assign_volunteer():
    """Assign a volunteer to a job"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        application = HRService.assign_volunteer_to_job(
            data['volunteer_id'],
            data['job_id']
        )
        return jsonify({
            'message': 'Volunteer assigned successfully',
            'application_id': application.id
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@hr_bp.route('/volunteers/<int:volunteer_id>/applications', methods=['GET'])
@jwt_required()
def get_volunteer_applications(volunteer_id):
    """Get all applications for a specific volunteer"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    applications = HRService.get_volunteer_applications(volunteer_id)
    return jsonify([{
        'id': app.id,
        'job_title': app.job.title,
        'status': app.status,
        'application_date': app.application_date.isoformat()
    } for app in applications]), 200


@hr_bp.route('/jobs/<int:job_id>/applications', methods=['GET'])
@jwt_required()
def get_job_applications(job_id):
    """Get all applications for a specific job"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    applications = HRService.get_job_applications(job_id)
    return jsonify([{
        'id': app.id,
        'volunteer_name': app.volunteer.full_name,
        'status': app.status,
        'application_date': app.application_date.isoformat()
    } for app in applications]), 200


@hr_bp.route('/volunteers/<int:volunteer_id>', methods=['PUT'])
@jwt_required()
def update_volunteer(volunteer_id):
    """Update volunteer information"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'hr':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        volunteer = HRService.update_volunteer(volunteer_id, data)
        return jsonify({
            'message': 'Volunteer updated successfully',
            'volunteer_id': volunteer.id
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest

from services.volunteer_service import VolunteerService
from models import User, Job
from utils.helpers import calculate_age

volunteer_bp = Blueprint('volunteer', __name__)


@volunteer_bp.route('/jobs', methods=['GET'])
@jwt_required()
def get_available_jobs():
    jobs = Job.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': job.id,
        'title': job.title,
        'description': job.description,
        'vacant_positions': job.vacant_positions,
        'required_certificates': job.required_certificates,
        'required_languages': job.required_languages,
        'additional_info': job.additional_info,
        'questions': [{
            'id': question.id,
            'job_id': question.job_id,
            'question_text': question.question_text,
            'answer_text': question.answer_text
        } for question in job.questions] if job.questions else [],
        'experience': job.experience,
        'education': job.education,
        'passed_courses': job.passed_courses,
        'tech_skills': job.tech_skills,
        'unit': job.unit,
        'status': job.status.name

    } for job in jobs]), 200


@volunteer_bp.route('/jobs/<int:job_id>/apply', methods=['POST', 'DELETE'])
@jwt_required()
def apply_for_job(job_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'volunteer':
        return jsonify({'message': 'Unauthorized'}), 403

    if request.method == 'POST':
        try:
            data = request.get_json()
            application = VolunteerService.apply_for_job(current_user.volunteer.id, job_id, data)
            return jsonify({'message': 'Application submitted successfully'}), 201
        except BadRequest as e:
            return jsonify({'message': str(e)}), 400
        except Exception as e:
            return jsonify({'message': 'An error occurred: ' + str(e)}), 500

    elif request.method == 'DELETE':
        application = VolunteerService.delete_application(current_user.volunteer.id, job_id)
        if application:
            return jsonify({'message': 'Application deleted successfully'}), 200
        else:
            return jsonify({'message': 'No application found'}), 404

    else:
        return jsonify({'message': 'Method not allowed'}), 405


def format_date_of_birth(data):
    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            date_obj = datetime.strptime(data['date_of_birth'], '%Y-%b-%d')
            data['date_of_birth'] = date_obj.strftime('%Y-%m-%dT00:00:00.000Z')
        except ValueError as e:
            raise BadRequest('Invalid date format for date_of_birth. Use YYYY-MMM-DD format (e.g., 2000-Nov-11)')
    return data


@volunteer_bp.route('/<int:volunteer_id>', methods=['PATCH'])
@jwt_required()
def update_volunteer(volunteer_id):
    current_user = User.query.get(get_jwt_identity())

    if current_user.volunteer.id != volunteer_id:
        return jsonify({'message': 'Unauthorized'}), 403
    try:
        data = request.get_json()

        # Format the date before updating
        formatted_data = format_date_of_birth(data)

        updated_volunteer = VolunteerService.update_volunteer_details(volunteer_id, formatted_data)

        if not updated_volunteer:
            return jsonify({'message': 'Volunteer not found'}), 404

        return jsonify({
            'id': updated_volunteer.id,
            'full_name': updated_volunteer.full_name,
            'address': updated_volunteer.address,
            'primary_profession': updated_volunteer.primary_profession,
            'education': updated_volunteer.education,
            'area_of_interest': updated_volunteer.area_of_interest,
            'contact_reference': updated_volunteer.contact_reference,
            'profile': updated_volunteer.profile,
            'date_of_birth': updated_volunteer.date_of_birth.isoformat() if updated_volunteer.date_of_birth else None,
            'gender': updated_volunteer.gender.value if updated_volunteer.gender else None,
            'experience': updated_volunteer.experience,
            'courses': updated_volunteer.courses,
            'languages': updated_volunteer.languages,
            'interests': updated_volunteer.interests,
            'personal_summary': updated_volunteer.personal_summary,
            'phone': updated_volunteer.user.phone,
            'email': updated_volunteer.user.email,
            'imageUrl': updated_volunteer.user.image_url
        }), 200
    except BadRequest as e:
        print(e)
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({'message': 'An error occurred: ' + str(e)}), 500


@volunteer_bp.route('/jobs/<int:job_id>/resume', methods=['POST'])
@jwt_required()
def upload_resume(job_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'volunteer':
        return jsonify({'message': 'Unauthorized'}), 403

    if 'resume' not in request.files:
        return jsonify({'message': 'No resume file uploaded'}), 400

    resume_file = request.files['resume']
    original_filename = resume_file.filename  # Access the original filename

    try:
        resume = VolunteerService.upload_resume(current_user.volunteer.id, job_id, resume_file)
        # You can potentially use the original_filename in the service call
        return jsonify({'message': 'Resume uploaded successfully', 'resume_id': resume.id}), 201
    except BadRequest as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({'message': 'Internal server error'}), 500


@volunteer_bp.route('/jobs/<int:job_id>/check-application', methods=['GET'])
@jwt_required()
def check_application(job_id):
    current_user = User.query.get(get_jwt_identity())
    already_applied = VolunteerService.check_if_applied(current_user.volunteer.id, job_id)
    return jsonify({'alreadyApplied': already_applied}), 200



@volunteer_bp.route('/get-profile-details', methods=['GET'])
@jwt_required()
def get_profile_details():
    current_user_id = get_jwt_identity()
    print(f"User ID from JWT: {current_user_id}")

    try:
        user = User.query.get(int(current_user_id))
        if not user:
            return jsonify({'message': 'User not found'}), 404

        if user.role != 'volunteer':
            return jsonify({'message': 'User is not a volunteer'}), 403

        volunteer = VolunteerService.get_user_info(user.id)
        if not volunteer:
            return jsonify({'message': 'Volunteer profile not found'}), 404

        response = {
            'email': volunteer.user.email,
            'phone': volunteer.user.phone,
            'id': volunteer.id,
            'full_name': volunteer.full_name,
            'national_id': volunteer.national_id,
            'address': volunteer.address,
            'primary_profession': volunteer.primary_profession,
            'education': volunteer.education,
            'area_of_interest': volunteer.area_of_interest,
            'profile': volunteer.profile,
            'date_of_birth': volunteer.date_of_birth.strftime('%Y-%m-%d') if volunteer.date_of_birth else None,
            'age': calculate_age(volunteer.date_of_birth) if volunteer.date_of_birth else None,
            'gender': volunteer.gender.name if volunteer.gender else None,
            'experience': volunteer.experience,
            'courses': volunteer.courses,
            'languages': volunteer.languages,
            'interests': volunteer.interests,
            'personal_summary': volunteer.personal_summary,
            'imageUrl': volunteer.user.image_url
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"Error in get_profile_details: {e}") # Print the full error for debugging
        return jsonify({'message': 'An error occurred'}), 500  # Return a generic error message to the client

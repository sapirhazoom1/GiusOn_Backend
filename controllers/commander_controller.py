import os
from datetime import date
from flask import Blueprint, request, jsonify, send_file, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest

from models import Resume, JobApplication
from services.commander_service import CommanderService
from models.user import User
import io

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from datetime import datetime, timedelta
import pytz

commander_bp = Blueprint('commander', __name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET")
if not CLIENT_SECRET_FILE:
    raise RuntimeError("GOOGLE_CLIENT_SECRET environment variable is not set!")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, 'utils', CLIENT_SECRET_FILE)
TOKEN_FILE = os.path.join(BASE_DIR, 'utils', 'token1.pickle')
REDIRECT_URI = 'http://localhost:8080/'


def get_calendar_service():
    """Get or create Calendar API service"""
    creds = None

    # Check if token file exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"Client secret file not found at {CLIENT_SECRET_FILE}. "
                    "Please download it from Google Cloud Console and place it in the config directory."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES,
                redirect_uri=REDIRECT_URI
            )
            creds = flow.run_local_server(port=8080)

            # Save the credentials for future use
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


@commander_bp.route('/send-interview-invitation', methods=['POST'])
@jwt_required()
def invite_interview():
    """Schedule an interview and send calendar invitations to both candidate and commander"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        # Get the calendar service using our configuration
        service = get_calendar_service()

        data = request.get_json()
        required_fields = ['candidate_email', 'commander_email', 'job_title', 'interview_time']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Parse the interview time
        try:
            interview_time = datetime.fromisoformat(data['interview_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid interview time format. Use ISO 8601 format'}), 400

        # Set interview duration
        interview_end = interview_time + timedelta(hours=1)

        event = {
            'summary': f'Interview for {data["job_title"]} Position',
            'location': 'Online',
            'description': f'''Interview for the position of {data["job_title"]}

        Commander: {data.get("commander_name", "Interview Commander")}
        Candidate: {data.get("candidate_name", "Candidate")}

        Additional Info: {data.get("additional_info", "")}''',
            'start': {
                'dateTime': interview_time.isoformat(),
                'timeZone': 'Asia/Jerusalem',
            },
            'end': {
                'dateTime': interview_end.isoformat(),
                'timeZone': 'Asia/Jerusalem',
            },
            'attendees': [
                {
                    'email': data['commander_email'],
                    'responseStatus': 'accepted',  # Auto-accept for organizer
                    'optional': False  # Mark as required attendee
                },
                {
                    'email': data['candidate_email'],
                    'responseStatus': 'needsAction',
                    'optional': False  # Mark as required attendee
                }
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30}
                ]
            },
            'guestsCanModify': False,  # Prevents attendees from modifying the event
            'guestsCanInviteOthers': False,  # Prevents attendees from inviting others
            'sendNotifications': True  # Explicitly request notifications
        }

        if data.get('include_meet_link', True):
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': f"interview-{datetime.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }

        try:
            event_result = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all',  # This ensures all attendees get notifications
                sendNotifications=True  # Additional parameter to force notifications
            ).execute()

            return jsonify({
                'message': 'Interview scheduled successfully',
                'event_link': event_result.get('htmlLink'),
                'meeting_link': event_result.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', None),
                'scheduled_time': interview_time.isoformat()
            }), 201

        except HttpError as error:
            return jsonify({'error': f'Calendar API error: {str(error)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@commander_bp.route('/jobs', methods=['POST'])
@jwt_required()
def create_job():
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    job = CommanderService.create_job(current_user.commander.id, data)

    return jsonify({
        'message': 'Job created successfully',
        'job_id': job.id
    }), 201


@commander_bp.route('/jobs', methods=['GET'])
@jwt_required()
def get_jobs():
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    jobs = CommanderService.get_commander_jobs(current_user.commander.id)
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
        'questions': [{
            'id': question.id,
            'job_id': question.job_id,
            'question_text': question.question_text,
            'answer_text': question.answer_text
        } for question in job.questions] if job.questions else [],
        # 'commonQuestions': job.common_questions,
        # 'commonAnswers': job.common_answers,
        'education': job.education,
        'techSkills': job.tech_skills,
        'workExperience': job.experience,
        'passedCourses': job.passed_courses,
        'candidateCount': len(job.applications),
        'status': job.status.name,
        'department': job.commander.department if job.commander else None,  # Get department from job
        'commanderId': job.commander_id,
        'applications_count': len(job.applications)
    } for job in jobs]

    return jsonify(payload), 200


@commander_bp.route('/jobs/<int:job_id>', methods=['PATCH'])
@jwt_required()
def patch_job_route(job_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    job = CommanderService.get_job_by_id(job_id)
    if not job:
        return jsonify({'message': 'Job not found'}), 404

    data = request.get_json()

    updated_job = CommanderService.patch_job(job, data)

    return jsonify({'message': 'Job updated successfully', 'job': {
        'id': str(updated_job.id),
        'jobName': updated_job.title,
        'jobCategory': updated_job.category,
        'unit': updated_job.unit,
        'address': updated_job.address,
        'positions': updated_job.vacant_positions,
        'openBase': updated_job.is_open_base,
        'closedBase': not updated_job.is_open_base,
        'jobDescription': updated_job.description,
        'additionalInfo': updated_job.additional_info,
        'questions': [{
            'id': question.id,
            'job_id': question.job_id,
            'question_text': question.question_text,
            'answer_text': question.answer_text
        } for question in job.questions] if job.questions else [],
        'education': updated_job.education,
        'techSkills': updated_job.tech_skills,
        'workExperience': updated_job.experience,
        'passedCourses': updated_job.passed_courses,
        'candidateCount': len(updated_job.applications),
        'status': updated_job.status.name,
        'department': updated_job.commander.department if updated_job.commander else None,  # Get department from job
        'commanderId': updated_job.commander_id,
        'applications_count': len(updated_job.applications)
    }}), 200


def calculate_age(born):
    today = date.today()
    try:
        birthday = born.replace(year=today.year)
    except ValueError:
        birthday = born.replace(year=today.year, day=born.day - 1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year


@commander_bp.route('/jobs/<int:job_id>/applications', methods=['GET'])
@jwt_required()
def get_job_applications(job_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    applications = CommanderService.get_job_applications(job_id, current_user.commander.id)
    return jsonify([{
        'candidateUserId': app.volunteer.id,
        'name': app.volunteer.full_name,
        'age': calculate_age(app.volunteer.date_of_birth) if app.volunteer.date_of_birth else None,
        'status': app.status.value,
        'imageUrl': app.volunteer.user.image_url
    } for app in applications]), 200


@commander_bp.route('/jobs/<int:job_id>/volunteers/<int:volunteer_id>', methods=['PATCH'])
@jwt_required()
def update_job_application_status(job_id, volunteer_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        updated_application = CommanderService.patch_job_application_status(job_id, volunteer_id, request.get_json())
        return jsonify({'message': 'Job application status updated successfully', 'application': {
            'id': str(updated_application.id),
            'status': updated_application.status.name,
        }}), 200
    except BadRequest as e:
        return jsonify({"message": str(e)}), 400


@commander_bp.route('/jobs/<int:job_id>/volunteers/<int:user_id>/interviews', methods=['POST', 'GET', 'PATCH', 'DELETE'])
@jwt_required()
def interview_management(job_id, user_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    try:
        if request.method == 'POST':
            data = request.get_json()
            interview = CommanderService.create_interview(job_id, user_id, data)
            return jsonify({'message': 'Interview created successfully', 'interview': {
                "candidateId": str(user_id),
                "jobId": str(job_id),
                "interviewNotes": interview.general_info,
                "interviewDate": interview.scheduled_date.isoformat() if interview.scheduled_date else None,
                "automaticMessage": interview.schedule,
                "status": interview.status
            }}), 201

        elif request.method == 'GET':
            interview = CommanderService.get_interview(job_id, user_id)
            if not interview:
                return jsonify({'message': 'Interview not found'}), 404
            return jsonify({
                "candidateId": str(user_id),
                "jobId": str(job_id),
                'applicationId':interview.application_id,
                "interviewNotes": interview.general_info,
                "interviewDate": interview.scheduled_date.isoformat() if interview.scheduled_date else None,
                "automaticMessage": interview.schedule,
                "status": interview.status
            }), 200

        elif request.method == 'PATCH':
            data = request.get_json()
            interview = CommanderService.patch_interview(job_id, user_id, data)
            if not interview:
                return jsonify({'message': 'Interview not found'}), 404
            return jsonify({
                "candidateId": str(user_id),
                "jobId": str(job_id),
                "interviewNotes": interview.general_info,
                "interviewDate": interview.scheduled_date.isoformat() if interview.scheduled_date else None,
                "automaticMessage": interview.schedule,
                "status": interview.status
            }), 200
        elif request.method == 'DELETE':
            CommanderService.delete_interview(job_id, user_id)
            return jsonify({'message': 'Interview deleted successfully'}), 200

    except BadRequest as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An error occurred: " + str(e)}), 500


@commander_bp.route('/volunteers/<int:volunteer_id>', methods=['GET'])
@jwt_required()
def get_volunteer(volunteer_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    current_commander_id = current_user.id
    print('id of commander is', current_commander_id)
    volunteer = CommanderService.get_volunteer_if_applied_to_commander_jobs(current_commander_id, volunteer_id)

    if not volunteer:
        return jsonify({'message': 'Volunteer has not applied to any of your jobs'}), 404

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


@commander_bp.route('/applications/<int:application_id>/status', methods=['PUT'])
@jwt_required()
def update_application_status(application_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    application = CommanderService.update_application_status(
        application_id,
        current_user.commander.id,
        data['status']
    )
    return jsonify({'message': 'Status updated successfully'}), 200


@commander_bp.route('/applications/<int:application_id>/interview', methods=['POST'])
@jwt_required()
def schedule_interview(application_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    interview = CommanderService.schedule_interview(
        application_id,
        current_user.commander.id,
        data
    )
    return jsonify({
        'message': 'Interview scheduled successfully',
        'interview_id': interview.id
    }), 201


@commander_bp.route('/jobs/<int:job_id>/volunteers/<int:user_id>/resume', methods=['GET'])
@jwt_required()
def get_resume_for_application(job_id, user_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=user_id).first()
    if not application:
        return jsonify({'message': 'Application not found'}), 404

    resume = Resume.query.filter_by(application_id=application.id).first()
    if not resume:
        return jsonify({'message': 'Resume not found for this application'}), 404

    resumes_folder = current_app.config['RESUMES_FOLDER']
    upload_folder = current_app.config['UPLOAD_FOLDER']
    full_path = os.path.join(upload_folder, resumes_folder, resume.file_path)

    if not os.path.exists(full_path):
        return jsonify({'message': 'File not found on server'}), 404

    uploads_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    resumes_path = os.path.join(uploads_path, current_app.config['RESUMES_FOLDER'])
    filename = resume.file_path
    try:
        return send_from_directory(resumes_path, filename)
        # return send_from_directory(resumes_path, filename, as_attachment=True, download_name="resume.pdf")
    except FileNotFoundError:
        return jsonify({'message': 'File not found on server'}), 404
    except Exception as e:
        return jsonify({'message': f'An unexpected error occurred: {str(e)}'}), 500  # Return JSON error
    # return jsonify({
    #     'file_path': resume.file_path,
    #     'application_id': resume.application_id,
    #     # ... other resume details
    # }), 200


@commander_bp.route('/jobs/<int:job_id>/applications/export', methods=['GET'])
@jwt_required()
def export_applications(job_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != 'commander':
        return jsonify({'message': 'Unauthorized'}), 403

    csv_data = CommanderService.generate_applications_csv(job_id, current_user.commander.id)
    if not csv_data:
        return jsonify({'message': 'No applications found'}), 404

    output = io.StringIO(csv_data)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'applications_job_{job_id}.csv'
    )

from flask_jwt_extended import get_jwt_identity

from models import Volunteer
from models.commander import Commander
from models.job import Job, JobQuestion, JobStatus
from models.interview import Interview
from models.application import JobApplication, ApplicationStatus
from db import db
from datetime import datetime
from flask import abort
import csv
import io
from werkzeug.exceptions import BadRequest
from models.user import User


class CommanderService:
    @staticmethod
    def create_commander(user_id, data):
        commander = Commander(
            user_id=user_id,
            name=data['name'],
            department=data.get('department'),
            rank=data.get('rank'),
            phone=data.get('phone')
        )
        db.session.add(commander)
        db.session.commit()
        return commander

    @staticmethod
    def create_job(commander_id, data):

        job = Job(
            commander_id=commander_id,
            title=data['name'],  # Map name to title
            description=data['description'],
            vacant_positions=data.get('positions', 1),
            category=data.get('category'),
            unit=data.get('unit'),
            address=data.get('address'),
            is_open_base=data.get('openBase', True),
            additional_info=data.get('additionalInfo'),
            experience=data.get('workExperience'),
            education=data.get('education'),
            passed_courses=data.get('passedCourses'),
            tech_skills=data.get('techSkills'),
        )

        db.session.add(job)

        for question_data in data.get('questions', []):
            question = JobQuestion(
                job=job,
                question_text=question_data['question_text'],
                answer_text=question_data['answer_text'],
                # required=question_data.get('required', True)
            )
            db.session.add(question)

        db.session.commit()
        return job

    @staticmethod
    def get_commander_jobs(commander_id):
        return Job.query.filter_by(commander_id=commander_id).all()

    @staticmethod
    def get_job_by_id(job_id):
        return Job.query.get(job_id)

    # @staticmethod
    # def patch_job(job, data):
    #     data = {k.lower(): v for k, v in data.items()}
    #
    #     field_mapping = {
    #         'name': 'title',
    #         'description': 'description',
    #         'positions': 'vacant_positions',
    #         'category': 'category',
    #         'unit': 'unit',
    #         'address': 'address',
    #         'openbase': 'is_open_base',
    #         'additionalinfo': 'additional_info',
    #         'questions': 'questions',  # Added questions mapping
    #         'workexperience': 'experience',
    #         'education': 'education',
    #         'passedcourses': 'passed_courses',
    #         'techskills': 'tech_skills',
    #         'status': 'status'
    #     }
    #     print(data)
    #     for frontend_key, model_field in field_mapping.items():
    #         if frontend_key in data:
    #             print(frontend_key, model_field)
    #             value = data[frontend_key]
    #
    #             if model_field == 'status':
    #                 try:
    #                     value = JobStatus(value)
    #                 except ValueError:
    #                     raise BadRequest(f"Invalid status value: {value}")
    #             setattr(job, model_field, value)
    #
    #     db.session.commit()
    #     return job
    @staticmethod
    def patch_job(job, data):
        data = {k.lower(): v for k, v in data.items()}

        field_mapping = {
            'name': 'title',
            'description': 'description',
            'positions': 'vacant_positions',
            'category': 'category',
            'unit': 'unit',
            'address': 'address',
            'openbase': 'is_open_base',
            'additionalinfo': 'additional_info',
            'questions': 'questions',
            'workexperience': 'experience',
            'education': 'education',
            'passedcourses': 'passed_courses',
            'techskills': 'tech_skills',
            'status': 'status'
        }

        for frontend_key, model_field in field_mapping.items():
            if frontend_key in data:
                value = data[frontend_key]

                if model_field == 'status':
                    try:
                        value = JobStatus(value)
                    except ValueError:
                        raise BadRequest(f"Invalid status value: {value}")
                elif model_field == 'questions':
                    existing_questions = {q.id: q for q in job.questions}

                    # Update or create questions
                    for question_data in value:
                        question_id = question_data.get('id')

                        if question_id and question_id in existing_questions:
                            # Update existing question
                            question = existing_questions[question_id]
                            question.question_text = question_data.get('question_text', question.question_text)
                            question.answer_text = question_data.get('answer_text', question.answer_text)
                            # Remove from existing_questions dict to track which ones to keep
                            existing_questions.pop(question_id)
                        else:
                            # Create new question
                            new_question = JobQuestion(
                                job_id=job.id,
                                question_text=question_data.get('question_text'),
                                answer_text=question_data.get('answer_text')
                            )
                            db.session.add(new_question)

                    # Delete questions that weren't in the update
                    for question in existing_questions.values():
                        db.session.delete(question)

                    continue  # Skip the setattr for questions

                setattr(job, model_field, value)

        db.session.commit()
        return job
    @staticmethod
    def get_volunteer_by_id(volunteer_id):
        return Volunteer.query.get_or_404(volunteer_id)

    @staticmethod
    def get_volunteer_if_applied_to_commander_jobs(commander_id, volunteer_id):
        has_applied = JobApplication.query.join(Job).filter(
            Job.commander_id == commander_id,
            JobApplication.volunteer_id == volunteer_id
        ).first()

        if not has_applied:
            return None  # Return None if not applied

        return Volunteer.query.get_or_404(volunteer_id)  # get volunteer if has applied

    @staticmethod
    def get_job_applications(job_id, commander_id):
        job = Job.query.filter_by(id=job_id, commander_id=commander_id).first()
        if not job:
            abort(404)
        return JobApplication.query.filter_by(job_id=job_id).all()

    @staticmethod
    def update_application_status(application_id, commander_id, status):
        application = JobApplication.query.get_or_404(application_id)
        if application.job.commander_id != commander_id:
            abort(403)
        application.status = status
        db.session.commit()
        return application

    @staticmethod
    def patch_job_application_status(job_id, volunteer_id, data):
        if 'status' not in data:
            raise BadRequest("Missing 'status' field in request data.")

        try:
            status_value = ApplicationStatus(data['status'])
        except ValueError:
            raise BadRequest(f"Invalid status value: {data['status']}")

        application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=volunteer_id).first()

        if not application:
            raise BadRequest('Job application not found')

        commander_id = get_jwt_identity()
        job = Job.query.get(job_id)

        if not job or str(job.commander_id) != str(commander_id):
            raise BadRequest("You don't have permission to update this application.")

        application.status = status_value
        db.session.commit()
        return application

    @staticmethod
    def create_interview(job_id, user_id, data):
        user = User.query.get(user_id)
        application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=user_id).first()
        if not application:
            raise BadRequest('Job application not found')

        scheduled_date_str = data.get('interviewDate')
        scheduled_date = None  # Default to None if no date is provided
        if scheduled_date_str:
            try:
                # scheduled_date = datetime.fromisoformat(scheduled_date_str)  # convert to datetime
                scheduled_date = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00'))  # convert to datetime
            except ValueError:
                raise BadRequest("Invalid date format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).")

        interview = Interview(
            application_id=application.id,
            general_info=data.get('interviewNotes'),
            scheduled_date=scheduled_date,  # Now a datetime object or None
            schedule=data.get('automaticMessage'),
            status=data.get('status')
        )
        db.session.add(interview)
        db.session.commit()
        return interview

    @staticmethod
    def get_interview(job_id, user_id):
        user = User.query.get(user_id)
        application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=user_id).first()
        if not application:
            return None
        return application.interview

    @staticmethod
    def patch_interview(job_id, user_id, data):
        user = User.query.get(user_id)
        application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=user_id).first()

        # application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=volunteer_id).first()
        if not application:
            raise BadRequest('Job application not found')
        interview = application.interview
        if not interview:
            raise BadRequest('Interview not found')

        if "interviewNotes" in data:
            interview.general_info = data.get('interviewNotes')

        if "interviewDate" in data:
            scheduled_date_str = data.get('interviewDate')
            scheduled_date = None
            if scheduled_date_str:
                try:
                    scheduled_date_str = scheduled_date_str.replace('.000Z', '')
                    scheduled_date = datetime.fromisoformat(scheduled_date_str)
                    # scheduled_date = datetime.fromisoformat(scheduled_date_str)
                except ValueError:
                    raise BadRequest("Invalid date format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).")
            interview.scheduled_date = scheduled_date

        if "automaticMessage" in data:
            interview.schedule = data.get('automaticMessage')
        if "status" in data:
            interview.status = data.get('status')

        db.session.commit()
        return interview

    @staticmethod
    def delete_interview(job_id, user_id):
        user = User.query.get(user_id)
        application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=user_id).first()

        # application = JobApplication.query.filter_by(job_id=job_id, volunteer_id=volunteer_id).first()
        if not application:
            raise BadRequest('Job application not found')
        
        interview = application.interview
        if not interview:
            raise BadRequest('Interview not found')
        
        db.session.delete(interview)
        db.session.commit()
        return {"message": "Interview deleted successfully"}


    @staticmethod
    def schedule_interview(application_id, commander_id, interview_data):
        application = JobApplication.query.get_or_404(application_id)
        if application.job.commander_id != commander_id:
            abort(403)

        interview = Interview(
            application_id=application_id,
            scheduled_date=datetime.fromisoformat(interview_data['scheduled_date']),
            schedule=interview_data.get('schedule'),
            status='scheduled'
        )
        db.session.add(interview)
        application.status = 'interview_scheduled'
        db.session.commit()
        return interview

    @staticmethod
    def update_interview_results(interview_id, commander_id, results_data):
        interview = Interview.query.get_or_404(interview_id)
        if interview.application.job.commander_id != commander_id:
            abort(403)

        interview.management_results = results_data.get('management_results')
        interview.personal_results = results_data.get('personal_results')
        interview.summary = results_data.get('summary')
        interview.status = 'completed'
        db.session.commit()
        return interview

    @staticmethod
    def generate_applications_csv(job_id, commander_id):
        applications = JobApplication.query.filter_by(job_id=job_id).all()
        if not applications:
            return None

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Application ID', 'Volunteer Name', 'Status', 'Application Date',
                         'Phone', 'Email', 'Education', 'Interview Status'])

        # Write data
        for app in applications:
            writer.writerow([
                app.id,
                app.volunteer.full_name,
                app.status,
                app.application_date.strftime('%Y-%m-%d'),
                app.volunteer.phone,
                app.volunteer.user.email,
                app.volunteer.education,
                app.interview.status if app.interview else 'No interview'
            ])

        return output.getvalue()
    
    @staticmethod
    def get_commander_user_info(user_id):
        return User.query.filter_by(id=user_id).first()

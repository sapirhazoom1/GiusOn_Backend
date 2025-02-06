from datetime import datetime

from werkzeug.utils import secure_filename
from flask import current_app
from models import JobApplication, ApplicationAnswer, Resume, User, Interview
from db import db
import os
from models.volunteer import Volunteer
from models import Volunteer, Resume
from werkzeug.exceptions import BadRequest


class VolunteerService:

    @staticmethod
    def apply_for_job(volunteer_id, job_id, data):
        existing_application = JobApplication.query.filter_by(
            volunteer_id=volunteer_id, job_id=job_id).first()
        if existing_application:
            raise BadRequest("You have already applied for this job")

        application = JobApplication(
            volunteer_id=volunteer_id,
            job_id=job_id,
            **data  # Unpack data dictionary into keyword arguments
        )
        db.session.add(application)
        db.session.commit()
        return application

    # @staticmethod
    # def apply_for_job(volunteer_id, job_id, data):
    #     application = JobApplication(
    #         volunteer_id=volunteer_id,
    #         job_id=job_id
    #     )
    #     db.session.add(application)

        # # Add answers
        # for answer in data.get('answers', []):
        #     app_answer = ApplicationAnswer(
        #         application=application,
        #         question_id=answer['question_id'],
        #         answer_text=answer['text']
        #     )
        #     db.session.add(app_answer)

        # db.session.commit()
        # return application

    @staticmethod
    def delete_application(volunteer_id, job_id):
        application = JobApplication.query.filter_by(
            volunteer_id=volunteer_id, job_id=job_id).first()
        if not application:
            return None
        Interview.query.filter_by(application_id=application.id).delete()
        db.session.delete(application)
        db.session.commit()
        return application

    @staticmethod
    def upload_resume(volunteer_id, job_id, resume_file):
        allowed_file_extensions = {'pdf', 'doc', 'docx', 'txt'}
        filename_parts = resume_file.filename.rsplit('.', 1)
        if len(filename_parts) == 1:
            raise BadRequest("Filename has no extension")

        file_extension = filename_parts[1].lower()

        if file_extension not in allowed_file_extensions:
            raise BadRequest("Invalid file format. Allowed extensions: " + ', '.join(allowed_file_extensions))

        application = JobApplication.query.filter_by(volunteer_id=volunteer_id, job_id=job_id).first()
        if not application:
            raise BadRequest("You must apply for the job first before uploading a resume")

        existing_resume = Resume.query.filter_by(application_id=application.id).first()
        if existing_resume:
            raise BadRequest("A resume has already been uploaded for this application")

        filename = secure_filename(resume_file.filename)
        resumes_folder = current_app.config['RESUMES_FOLDER']
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(os.path.join(upload_folder, resumes_folder), exist_ok=True)

        full_file_path = os.path.join(upload_folder, resumes_folder, filename)

        resume_file.save(full_file_path)

        resume = Resume(
            application_id=application.id,
            file_path=filename  # Store ONLY the filename in the database
        )
        db.session.add(resume)
        db.session.commit()
        return resume


    @staticmethod
    def get_user_info(user_id):
        return Volunteer.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_volunteer_by_user_id(user_id):
        user = User.query.get(user_id)
        if not user or not user.volunteer:
            return None
        return user.volunteer

    @staticmethod
    def update_volunteer_details(volunteer_id, data):
        volunteer = Volunteer.query.get(volunteer_id)
        if not volunteer:
            raise BadRequest("Volunteer not found")

        user = volunteer.user

        volunteer_data = {}
        user_data = {}

        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                date_str = data['date_of_birth']
                date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ').date()
                data['date_of_birth'] = date_obj
            except ValueError:
                raise BadRequest(
                    "Invalid date format for date_of_birth. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssZ).")
        else:
            del data['date_of_birth']

        for key, value in data.items():
            if hasattr(volunteer, key):
                volunteer_data[key] = value
            elif hasattr(user, key):
                user_data[key] = value
            else:
                raise BadRequest(f"Invalid field to update: {key}")

        # Update Volunteer fields
        for key, value in volunteer_data.items():
            setattr(volunteer, key, value)

        # Update User fields
        for key, value in user_data.items():
            setattr(user, key, value)

        db.session.commit()
        return volunteer

    @staticmethod
    def check_if_applied(volunteer_id, job_id):
        existing_application = JobApplication.query.filter_by(
            volunteer_id=volunteer_id, job_id=job_id).first()
        return existing_application is not None
# services/hr_service.py
from datetime import datetime
from random import randint
from models import User, HR, Volunteer, JobApplication, Job
from models.volunteer import Gender
from services.auth_service import AuthService
from db import db
from flask import abort, jsonify


class HRService:
    @staticmethod
    def create_hr_user(data):
        try:
            # Create base user with HR role
            user,_ = AuthService.create_user(
                email=data['email'],
                password=data['password'],
                role='hr'
            )
            db.session.add(user)

            # Create HR profile
            hr = HR(
                user=user,
                name=data['name'],
                department=data.get('department'),
                phone=data.get('phone')
            )
            db.session.add(hr)
            db.session.commit()
            return hr
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def create_volunteer(data):
        try:
            image_url = f"https://mighty.tools/mockmind-api/content/human/{randint(1, 130)}.jpg"
            # Check if user already exists
            email = data.get('email')
            if User.query.filter_by(email=email).first():
                return None, f"User with email {email} already exists"

            # Prepare user data
            user_fields = {
                'email': data['email'],
                'role': 'volunteer',
                'phone': data.get('phone'),
                'full_name': data.get('full_name'),
                'image_url': image_url
            }

            # Prepare volunteer data
            volunteer_fields = {
                'full_name': data['full_name'],
                'national_id': data['national_id'],
                # 'address': data.get('address'),
                # 'primary_profession': data.get('primary_profession'),
                # 'education': data.get('education'),
                # 'area_of_interest': data.get('area_of_interest'),
                # 'contact_reference': data.get('contact_reference'),
                # 'profile': data.get('profile'),
                # 'date_of_birth': data.get('date_of_birth'),
                # 'gender': data.get('gender'),
                # 'experience': data.get('experience'),
                # 'courses': data.get('courses'),
                # 'languages': data.get('languages'),
                # 'interests': data.get('interests'),
                # 'personal_summary': data.get('personal_summary')
            }

            # Create user
            user = User(**{k: v for k, v in user_fields.items() if v is not None})
            user.set_password(data['national_id'])
            db.session.add(user)
            db.session.flush()  # Get user.id before creating volunteer

            # Create volunteer with user_id
            volunteer_fields['user_id'] = user.id
            volunteer = Volunteer(**{k: v for k, v in volunteer_fields.items() if v is not None})
            db.session.add(volunteer)

            try:
                db.session.commit()
                return volunteer, None
            except Exception as e:
                db.session.rollback()
                return None, f"Database error: {str(e)}"

        except Exception as e:
            print(f"Error in create_volunteer: {str(e)}")
            db.session.rollback()
            return None, str(e)


    @staticmethod
    def get_all_volunteers():
        return Volunteer.query.all()

    @staticmethod
    def get_volunteer_by_id(volunteer_id):
        return Volunteer.query.get_or_404(volunteer_id)

    @staticmethod
    def get_all_jobs():
        return Job.query.all()

    @staticmethod
    def assign_volunteer_to_job(volunteer_id, job_id):
        try:
            volunteer = Volunteer.query.get_or_404(volunteer_id)
            job = Job.query.get_or_404(job_id)

            application = JobApplication.query.filter_by(
                volunteer_id=volunteer_id,
                job_id=job_id
            ).first()

            print(application.status)

            if not application:
                abort(404, description="Application Not Found!")
                
            applicationStatus = str(application.status)
            if applicationStatus.strip().lower() != 'preferred_final':
                abort(400, description="Application must be accepted by commander first")

            if job.vacant_positions <= 0:
                abort(400, description="No vacant positions available")

            job.vacant_positions -= 1

            application.status = 'HIRED'

            if job.vacant_positions == 0:
                job.status = 'CLOSED'

            db.session.commit()
            return application
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_volunteer_applications(volunteer_id):
        return JobApplication.query.filter_by(volunteer_id=volunteer_id).all()

    @staticmethod
    def get_job_applications(job_id):
        return JobApplication.query.filter_by(job_id=job_id).all()

    @staticmethod
    def update_volunteer(volunteer_id, data):
        try:
            volunteer = Volunteer.query.get_or_404(volunteer_id)

            # Update volunteer fields
            # for key, value in data.items():
            #     if hasattr(volunteer, key):
            #         setattr(volunteer, key, value)

            for key, value in data.items():
                if key == "profile":
                    try:
                        setattr(volunteer, key, int(value) if value is not None else None)
                    except (ValueError, TypeError):
                        return jsonify({"error": "Invalid profile value (must be an integer)"}), 400
                elif key == "date_of_birth":
                    if value:
                        try:
                            date_object = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                            setattr(volunteer, key, date_object)
                        except ValueError:
                            return jsonify({"error": "Invalid date format"}), 400
                    else:
                        setattr(volunteer, key, None)
                elif key == "gender":
                    if value:
                        try:
                            # Correct Enum Lookup (by value, case-insensitive)
                            volunteer.gender = Gender(value.title())
                        except ValueError:
                            return jsonify({"error": f"Invalid gender: {value}"}), 400
                    else:
                        volunteer.gender = None
                elif hasattr(volunteer, key):
                    setattr(volunteer, key, value)
            db.session.commit()
            return volunteer
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_hr_user_info(user_id):
        return User.query.filter_by(id=user_id).first()

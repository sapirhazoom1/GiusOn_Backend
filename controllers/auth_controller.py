from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from services.auth_service import AuthService
from services.commander_service import CommanderService
from services.hr_service import HRService
from services.volunteer_service import VolunteerService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        email = data['email']
        password = data['password']
        role = data['role']
        user_data = {k: v for k, v in data.items() if k not in ['email', 'password', 'role']}
        user, error = AuthService.create_user(email, password, role, **user_data)

        if error:
            return jsonify({"message": f"Error creating user: {error}"}), 400

        return jsonify({"message": "User created successfully"}), 201
    except KeyError as e:
        return jsonify({"message": f"Missing field: {e}"}), 400
    except Exception as e:
        return jsonify({"message": f"An unexpected error occurred: {str(e)}"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Missing email or password'}), 400
        
    token, role, user_id = AuthService.login(email, password)
    
    if not token:
        return jsonify({'message': 'Invalid credentials'}), 401
        
    response = {
        'access_token': token,
        'role': role
    }
    
    if role == 'volunteer':
        volunteer = VolunteerService.get_user_info(user_id)
        if volunteer:
            response['user'] = {
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
                'date_of_birth': volunteer.date_of_birth.strftime('%Y-%b-%d') if volunteer.date_of_birth else None,
                'age': calculate_age(volunteer.date_of_birth) if volunteer.date_of_birth else None,
                'gender': volunteer.gender.name if volunteer.gender else None,
                'experience': volunteer.experience,
                'courses': volunteer.courses,
                'languages': volunteer.languages,
                'interests': volunteer.interests,
                'personal_summary': volunteer.personal_summary,
                'imageUrl': volunteer.user.image_url
            }
    elif role == 'hr':
        hr = HRService.get_hr_user_info(user_id)
        if hr:
            response['user'] = {
                'id': hr.id,
                'full_name': hr.full_name,
                'email': hr.email,
                'imageUrl': hr.image_url

            }
    elif role == 'commander':
        commander = CommanderService.get_commander_user_info(user_id)
        if commander:
            response['user'] = {
                'id': commander.id,
                'full_name': commander.full_name,
                'email': commander.email,
                'imageUrl': commander.image_url

            }
    
    return jsonify(response), 200

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

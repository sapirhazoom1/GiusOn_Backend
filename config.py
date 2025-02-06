import os
from datetime import timedelta

# class Config:
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///volunteer_system.db')
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
#     JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

class Config:
    # Absolute path to the database file
    db_path = os.path.join(os.getcwd(), 'volunteer_system.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key' # Use SECRET_KEY for JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Add these lines
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ALGORITHM = 'HS256'  # Explicitly set the algorithm
    JSON_AS_ASCII = False  #
    JSON_SORT_KEYS = False  # Sometimes helps with Windows encoding issues
    PROPAGATE_EXCEPTIONS = True  # This will help you see the actual error

    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    RESUMES_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')  # Subfolder for resumes
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limit

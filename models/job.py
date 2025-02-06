import enum

from db import db
from datetime import datetime


class JobStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    commander_id = db.Column(db.Integer, db.ForeignKey('commanders.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    vacant_positions = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    required_certificates = db.Column(db.String(200))
    required_languages = db.Column(db.String(200))


    #added columns
    status = db.Column(db.Enum(JobStatus), default=JobStatus.OPEN) #Status as enum
    is_open_base = db.Column(db.Boolean, default=True)  # Replaces OpenBase/ClosedBase
    description = db.Column(db.Text)
    additional_info = db.Column(db.Text)
    common_questions = db.Column(db.Text)
    common_answers = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)
    passed_courses = db.Column(db.Text)
    tech_skills = db.Column(db.Text)
    category = db.Column(db.String(100))
    unit = db.Column(db.String(100))
    address = db.Column(db.String(200))
    position = db.Column(db.String(100))
    # Relationships
    questions = db.relationship('JobQuestion', backref='job', lazy=True)
    applications = db.relationship('JobApplication', backref='job', lazy=True)


class JobQuestion(db.Model):
    __tablename__ = 'job_questions'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    # required = db.Column(db.Boolean, default=True)
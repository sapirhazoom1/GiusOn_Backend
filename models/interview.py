from db import db
from datetime import datetime

class Interview(db.Model):
    __tablename__ = 'interviews'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime)
    general_info = db.Column(db.Text)
    schedule = db.Column(db.Text)
    management_results = db.Column(db.Text)
    personal_results = db.Column(db.Text)
    summary = db.Column(db.Text)
    status = db.Column(db.String(20))  # scheduled, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

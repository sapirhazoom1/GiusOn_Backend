from db import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'commander', 'volunteer', 'hr'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    image_url = db.Column(db.String(255))  # Added image_url field
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))

    # full_name = db.Column(db.String(100), nullable=False) #make nulable later

    # Relationships
    volunteer = db.relationship('Volunteer', backref='user', uselist=False)
    commander = db.relationship('Commander', backref='user', uselist=False)
    hr = db.relationship('HR', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
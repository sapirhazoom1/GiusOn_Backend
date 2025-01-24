from db import db


class HR(db.Model):
    __tablename__ = 'hr_staff'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))

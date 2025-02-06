from db import db


class Commander(db.Model):
    __tablename__ = 'commanders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.String(50))
    department = db.Column(db.String(100))

    # Relationships
    jobs = db.relationship('Job', backref='commander', lazy=True)
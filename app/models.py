# app/models.py
from . import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='faculty')  # 'scheduler' or 'faculty'
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)  # Link to faculty record
    
    # Relationships
    faculty = db.relationship('Faculty', backref='user_account')
    votes = db.relationship('Vote', backref='user')
    
    def is_scheduler(self):
        return self.role == 'scheduler'
    
    def is_faculty(self):
        return self.role == 'faculty'


class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)


class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(150), nullable=False)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    hours_per_week = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)  # <- can be NULL


class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True)
    data = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)  # 1, 2, or 3 for the three options
    session_id = db.Column(db.String(100), nullable=False)  # Groups the 3 timetables together
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Current voting session
    vote_count = db.Column(db.Integer, default=0)  # Total votes for this timetable
    is_published = db.Column(db.Boolean, default=False)  # Marks the winning timetable as published
    published_at = db.Column(db.DateTime, nullable=True)  # When the results were published
    
    # Relationships
    votes = db.relationship('Vote', backref='timetable')


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)  # Ensures one vote per session per user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure one vote per user per session
    __table_args__ = (db.UniqueConstraint('user_id', 'session_id', name='unique_user_session_vote'),)


class TimetableParameters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Configuration
    num_classrooms = db.Column(db.Integer, default=10)
    num_batches = db.Column(db.Integer, default=6)
    max_classes_per_day = db.Column(db.Integer, default=6)
    
    # Subject Configuration
    total_subjects = db.Column(db.Integer, default=8)
    default_classes_per_week = db.Column(db.Integer, default=3)
    
    # Faculty Management
    total_faculties = db.Column(db.Integer, default=12)
    avg_monthly_leaves = db.Column(db.Integer, default=2)
    
    # Special Classes & Advanced
    fixed_time_slots = db.Column(db.Text, nullable=True)
    break_duration = db.Column(db.Integer, default=15)
    lunch_break_duration = db.Column(db.Integer, default=60)
    
    # Optimization Settings
    room_utilization_priority = db.Column(db.Integer, default=8)
    faculty_load_balance_priority = db.Column(db.Integer, default=7)
    no_gaps_priority = db.Column(db.Integer, default=6)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Current active configuration

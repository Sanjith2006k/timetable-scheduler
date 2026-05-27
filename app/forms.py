# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
from .models import Faculty

class ClassroomForm(FlaskForm):
    name = StringField('Classroom Name', validators=[DataRequired()])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Classroom')

class FacultyForm(FlaskForm):
    name = StringField('Faculty Name', validators=[DataRequired()])
    subject = StringField('Subject Expertise', validators=[DataRequired()])
    submit = SubmitField('Add Faculty')

class SubjectForm(FlaskForm):
    name = StringField('Subject Name', validators=[DataRequired()])
    hours_per_week = IntegerField('Hours per Week', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Subject')
   
# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response
from . import db, login_manager
from .models import User, Classroom, Faculty, Subject, Timetable, Vote, TimetableParameters
from flask_login import login_user, logout_user, login_required, current_user
from .forms import ClassroomForm, FacultyForm, SubjectForm
from .scheduler import generate_multiple_timetables, save_timetables_to_db  # Updated import
from functools import wraps
import json

main = Blueprint('main', __name__)

def scheduler_required(f):
    """Decorator to require scheduler role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_scheduler():
            flash('Access denied. Scheduler role required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def faculty_required(f):
    """Decorator to require faculty role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_faculty():
            flash('Access denied. Faculty role required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Login attempt - Username: '{username}', Password: '{password}'")  # Debug
        
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User found - Role: {user.role}, Stored password: '{user.password}'")  # Debug
            if user.password == password:
                login_user(user)
                print(f"Login successful for {username}")  # Debug
                return redirect(url_for('main.dashboard'))
            else:
                print(f"Password mismatch for {username}")  # Debug
                flash('Invalid username or password', 'error')
        else:
            print(f"User not found: {username}")  # Debug
            flash('Invalid username or password', 'error')
    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/add_classroom', methods=['GET', 'POST'])
@login_required
@scheduler_required
def add_classroom():
    form = ClassroomForm()
    if form.validate_on_submit():
        # Check if classroom name already exists
        existing_classroom = Classroom.query.filter_by(name=form.name.data).first()
        if existing_classroom:
            flash(f'Classroom "{form.name.data}" already exists. Please use a different name.', 'error')
            return render_template('add_classroom.html', form=form)
        
        try:
            new_classroom = Classroom(name=form.name.data, capacity=form.capacity.data)
            db.session.add(new_classroom)
            db.session.commit()
            flash('Classroom added successfully!', 'success')
            return redirect(url_for('main.dashboard') + '#classrooms')
        except Exception as e:
            db.session.rollback()
            flash('Error adding classroom. Please try again.', 'error')
            return render_template('add_classroom.html', form=form)
    return render_template('add_classroom.html', form=form)

@main.route('/add_faculty', methods=['GET', 'POST'])
@login_required
@scheduler_required
def add_faculty():
    form = FacultyForm()
    if form.validate_on_submit():
        try:
            # Create faculty record
            new_faculty = Faculty(name=form.name.data, subject=form.subject.data)
            db.session.add(new_faculty)
            db.session.flush()  # Get the faculty ID without committing
            
            # Create username from faculty name (lowercase, replace spaces with dots)
            username = form.name.data.lower().replace(' ', '.').replace('dr.', 'dr').replace('prof.', 'prof')
            # Remove any special characters except dots
            import re
            username = re.sub(r'[^a-z0-9.]', '', username)
            
            # Check if username already exists, add number if needed
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user account for the faculty
            new_user = User(
                username=username,
                password='faculty123',  # Default password
                role='faculty',
                faculty_id=new_faculty.id
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'Faculty added successfully! Login credentials - Username: {username}, Password: faculty123', 'success')
            return redirect(url_for('main.dashboard') + '#faculties')
        except Exception as e:
            db.session.rollback()
            flash('Error adding faculty. Please try again.', 'error')
            return render_template('add_faculty.html', form=form)
    return render_template('add_faculty.html', form=form)
@main.route('/add_subject', methods=['GET', 'POST'])
@login_required
@scheduler_required
def add_subject():
    form = SubjectForm()
    if form.validate_on_submit():
        # Allow faculty_id to be None for temporary subjects
        new_subject = Subject(
            name=form.name.data,
            hours_per_week=form.hours_per_week.data,
            faculty_id=None  # explicitly set to None
        )
        db.session.add(new_subject)
        db.session.commit()
        flash('Subject added successfully!')
        return redirect(url_for('main.dashboard') + '#subjects')
    return render_template('add_subject.html', form=form)

@main.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
@scheduler_required
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    if form.validate_on_submit():
        subject.name = form.name.data
        subject.hours_per_week = form.hours_per_week.data
        db.session.commit()
        flash('Subject updated successfully!')
        return redirect(url_for('main.dashboard') + '#subjects')
    return render_template('edit_subject.html', form=form)

@main.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
@scheduler_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('main.dashboard') + '#subjects')
@main.route('/edit_faculty/<int:faculty_id>', methods=['GET', 'POST'])
@login_required
@scheduler_required
def edit_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    form = FacultyForm(obj=faculty)
    if form.validate_on_submit():
        faculty.name = form.name.data
        faculty.subject = form.subject.data
        db.session.commit()
        flash('Faculty updated successfully!')
        return redirect(url_for('main.dashboard') + '#faculties')
    return render_template('edit_faculty.html', form=form)

@main.route('/delete_faculty/<int:faculty_id>', methods=['POST'])
@login_required
@scheduler_required
def delete_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    db.session.delete(faculty)
    db.session.commit()
    flash('Faculty deleted successfully!', 'success')
    return redirect(url_for('main.dashboard') + '#faculties')
@main.route('/edit_classroom/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
@scheduler_required
def edit_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    form = ClassroomForm(obj=classroom)
    if form.validate_on_submit():
        classroom.name = form.name.data
        classroom.capacity = form.capacity.data
        db.session.commit()
        flash('Classroom updated successfully!')
        return redirect(url_for('main.dashboard') + '#classrooms')
    return render_template('edit_classroom.html', form=form)

@main.route('/delete_classroom/<int:classroom_id>', methods=['POST'])
@login_required
@scheduler_required
def delete_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    db.session.delete(classroom)
    db.session.commit()
    flash('Classroom deleted successfully!', 'success')
    return redirect(url_for('main.dashboard') + '#classrooms')

# ✅ timetable routes - Updated for multiple timetables and voting
@main.route("/generate_timetables")
@login_required
@scheduler_required
def generate_timetables_view():
    """Generate 3 timetable options for voting"""
    timetables_list = generate_multiple_timetables(3)
    
    if not timetables_list:
        flash('Failed to generate timetables. Please check your data.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Save to database
    saved_timetables, session_id = save_timetables_to_db(timetables_list)
    
    flash(f'Successfully generated {len(saved_timetables)} timetable options for voting!', 'success')
    return redirect(url_for('main.view_voting_timetables'))

def get_faculty_workload(timetable_data):
    """Calculate current workload for each faculty member"""
    from .models import Faculty
    
    faculty_workload = {}
    all_faculty = Faculty.query.all()
    
    # Initialize workload counter for all faculty
    for faculty in all_faculty:
        faculty_workload[faculty.name] = 0
    
    # Count assigned classes for each faculty
    for classroom_name, classroom_schedule in timetable_data.items():
        for day, day_schedule in classroom_schedule.items():
            for slot, classes in day_schedule.items():
                if classes:
                    for class_info in classes:
                        if isinstance(class_info, str) and '|' in class_info:
                            parts = class_info.split('|')
                            if len(parts) >= 3:
                                faculty_name = parts[2]
                                if faculty_name != "TBD" and faculty_name in faculty_workload:
                                    faculty_workload[faculty_name] += 1
    
    return faculty_workload

def assign_faculty_to_free_slot(timetable_data, day, slot):
    """Assign a random available faculty to a free slot, balancing workload"""
    from .models import Faculty
    import random
    
    # Get all faculty
    all_faculty = Faculty.query.all()
    
    # Get currently busy faculty for this slot
    busy_faculty = set()
    for classroom_name, classroom_schedule in timetable_data.items():
        if day in classroom_schedule and slot in classroom_schedule[day]:
            classes = classroom_schedule[day][slot]
            if classes:
                for class_info in classes:
                    if isinstance(class_info, str) and '|' in class_info:
                        parts = class_info.split('|')
                        if len(parts) >= 3:
                            faculty_name = parts[2]
                            if faculty_name != "TBD":
                                busy_faculty.add(faculty_name)
    
    # Get available faculty
    available_faculty = [f.name for f in all_faculty if f.name not in busy_faculty]
    
    if not available_faculty:
        return "No Faculty Available"
    
    # Get current workload for all faculty
    faculty_workload = get_faculty_workload(timetable_data)
    
    # Filter available faculty and sort by workload (ascending - least busy first)
    available_with_workload = [(name, faculty_workload.get(name, 0)) for name in available_faculty]
    available_with_workload.sort(key=lambda x: x[1])
    
    # Get faculty with minimum workload
    min_workload = available_with_workload[0][1]
    least_busy_faculty = [name for name, workload in available_with_workload if workload == min_workload]
    
    # Randomly select from the least busy faculty
    selected_faculty = random.choice(least_busy_faculty)
    
    return selected_faculty

def consolidate_timetables(timetable_data):
    """Consolidate multiple classroom schedules into one unified view"""
    consolidated = {}
    
    # Initialize the consolidated structure
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slots = ['Slot 1', 'Slot 2', 'Slot 3', 'Slot 4', 'Slot 5', 'Slot 6']
    
    for day in days:
        consolidated[day] = {}
        for slot in slots:
            consolidated[day][slot] = []
    
    # Merge all classroom schedules
    for classroom_name, classroom_schedule in timetable_data.items():
        for day in days:
            if day in classroom_schedule:
                for slot in slots:
                    if slot in classroom_schedule[day] and classroom_schedule[day][slot]:
                        for class_info in classroom_schedule[day][slot]:
                            # Add classroom info to the class data
                            parts = class_info.split('|')
                            if len(parts) >= 3:
                                # Format: Subject|Classroom|Faculty
                                consolidated_entry = f"{parts[0]}|{classroom_name}|{parts[2]}"
                            else:
                                consolidated_entry = f"{parts[0]}|{classroom_name}"
                            
                            consolidated[day][slot].append(consolidated_entry)
    
    return consolidated

def get_available_faculty_for_slot(timetable_data, day, slot):
    """Get list of faculty available during a specific day/slot"""
    from .models import Faculty
    
    # Get all faculty
    all_faculty = Faculty.query.all()
    available_faculty = []
    
    # Check which faculty are not assigned to any classroom during this slot
    busy_faculty = set()
    
    # Check all classrooms for this day/slot to find busy faculty
    for classroom_name, classroom_schedule in timetable_data.items():
        if day in classroom_schedule and slot in classroom_schedule[day]:
            classes = classroom_schedule[day][slot]
            if classes:  # Only check if there are classes scheduled
                for class_info in classes:
                    if isinstance(class_info, str) and '|' in class_info:
                        parts = class_info.split('|')
                        if len(parts) >= 3:
                            faculty_name = parts[2]
                            if faculty_name != "TBD":
                                busy_faculty.add(faculty_name)
    
    # Find faculty who are not busy
    for faculty in all_faculty:
        if faculty.name not in busy_faculty:
            available_faculty.append(faculty.name)
    
    return available_faculty

@main.route("/voting_timetables")
@login_required
def view_voting_timetables():
    """View current timetables for voting (both scheduler and faculty can see)"""
    active_timetables = Timetable.query.filter_by(is_active=True).order_by(Timetable.version).all()
    
    if not active_timetables:
        flash('No active timetables available for voting.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Parse timetable data and consolidate
    timetables_with_data = []
    for tt in active_timetables:
        timetable_data = json.loads(tt.data)
        consolidated_data = consolidate_timetables(timetable_data)
        
        # DEBUG: Check consolidated data
        print(f"DEBUG VOTING: Timetable {tt.version} Monday Slot 5: {consolidated_data['Monday']['Slot 5']}")
        
        timetables_with_data.append({
            'id': tt.id,
            'name': tt.name,
            'version': tt.version,
            'vote_count': tt.vote_count,
            'data': {'Consolidated Schedule': consolidated_data}
        })
    
    # Check if current user has voted in this session
    user_vote = None
    if current_user.is_faculty() and active_timetables:
        user_vote = Vote.query.filter_by(
            user_id=current_user.id,
            session_id=active_timetables[0].session_id
        ).first()
    
    return render_template('voting_timetables.html', 
                         timetables=timetables_with_data,
                         user_vote=user_vote,
                         current_user=current_user,
                         assign_faculty_to_slot=assign_faculty_to_free_slot)

@main.route("/vote/<int:timetable_id>", methods=['POST'])
@login_required
@faculty_required
def vote_for_timetable(timetable_id):
    """Faculty votes for a timetable"""
    timetable = Timetable.query.get_or_404(timetable_id)
    
    if not timetable.is_active:
        flash('This voting session has ended.', 'error')
        return redirect(url_for('main.view_voting_timetables'))
    
    # Check if user already voted in this session
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        session_id=timetable.session_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        old_timetable = Timetable.query.get(existing_vote.timetable_id)
        old_timetable.vote_count -= 1
        
        existing_vote.timetable_id = timetable_id
        timetable.vote_count += 1
        
        flash('Your vote has been updated!', 'success')
    else:
        # Create new vote
        vote = Vote(
            user_id=current_user.id,
            timetable_id=timetable_id,
            session_id=timetable.session_id
        )
        db.session.add(vote)
        timetable.vote_count += 1
        
        flash('Your vote has been recorded!', 'success')
    
    db.session.commit()
    return redirect(url_for('main.view_voting_timetables'))

@main.route("/end_voting", methods=['POST'])
@login_required
@scheduler_required
def end_voting():
    """End current voting session and declare winner"""
    active_timetables = Timetable.query.filter_by(is_active=True).all()
    
    if not active_timetables:
        flash('No active voting session found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Find winning timetable
    winner = max(active_timetables, key=lambda t: t.vote_count)
    
    # Mark session as inactive
    for tt in active_timetables:
        tt.is_active = False
    
    # Mark winner as published
    from datetime import datetime
    winner.is_published = True
    winner.published_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Voting ended! {winner.name} won with {winner.vote_count} votes and has been published to all faculty.', 'success')
    return redirect(url_for('main.dashboard'))

@main.route("/published_timetable")
@login_required
def get_published_timetable():
    """Get the currently published winning timetable"""
    published_timetable = Timetable.query.filter_by(is_published=True).order_by(Timetable.published_at.desc()).first()
    
    if not published_timetable:
        flash('No published timetable available yet.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Parse and consolidate the timetable data
    timetable_data = json.loads(published_timetable.data)
    consolidated_data = consolidate_timetables(timetable_data)
    
    return render_template('published_timetable.html', 
                         timetable=published_timetable,
                         consolidated_data=consolidated_data,
                         current_user=current_user)

@main.route("/export_timetable_pdf")
@login_required
def export_timetable_pdf():
    """Export published timetable as PDF"""
    published_timetable = Timetable.query.filter_by(is_published=True).order_by(Timetable.published_at.desc()).first()
    
    if not published_timetable:
        flash('No published timetable available for export.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )
        
        # Title
        title = Paragraph(f"Final Timetable - {published_timetable.name}", title_style)
        elements.append(title)
        
        # Subtitle with voting info
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=1,
        )
        subtitle = Paragraph(f"Winner with {published_timetable.vote_count} votes - Published on {published_timetable.published_at.strftime('%B %d, %Y')}", subtitle_style)
        elements.append(subtitle)
        
        # Parse timetable data
        timetable_data = json.loads(published_timetable.data)
        consolidated_data = consolidate_timetables(timetable_data)
        
        # Create table data
        data = []
        
        # Header row
        header = ['Day/Time', 'Slot 1\n8:00-9:00', 'Slot 2\n9:00-10:00', 'Slot 3\n10:00-11:00', 
                 'Slot 4\n11:00-12:00', 'Slot 5\n12:00-1:00', 'Slot 6\n1:00-2:00']
        data.append(header)
        
        # Data rows
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        slots = ['Slot 1', 'Slot 2', 'Slot 3', 'Slot 4', 'Slot 5', 'Slot 6']
        
        for day in days:
            row = [day]
            for slot in slots:
                cell_content = []
                if consolidated_data[day][slot]:
                    for class_info in consolidated_data[day][slot]:
                        parts = class_info.split('|')
                        if len(parts) >= 3:
                            cell_content.append(f"{parts[0]}\n{parts[1]}\n{parts[2]}")
                if cell_content:
                    row.append('\n\n'.join(cell_content))
                else:
                    row.append('Free Period')
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[1*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
        
        # Table style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Timetable_{published_timetable.name.replace(" ", "_")}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('main.get_published_timetable'))

# Keep original generate_timetable for backward compatibility
@main.route("/generate_timetable")
@login_required
@scheduler_required
def generate_timetable_view():
    """Generate single timetable (legacy route)"""
    from .scheduler import generate_timetable
    raw = generate_timetable()  # your existing function
    all_timetables = {}

    # Convert raw data to classroom -> days -> slots structure
    for class_name, day_data in raw.items():  # ensure raw has classrooms
        all_timetables[class_name] = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            all_timetables[class_name][day] = day_data.get(day, {})
    
    return render_template("timetable.html", 
                         all_timetables=all_timetables,
                         assign_faculty_to_slot=assign_faculty_to_free_slot)


@main.route('/debug-timetable')
@login_required
def debug_timetable():
    """Debug route to show clean timetable data"""
    from .scheduler import generate_multiple_timetables
    
    # Generate fresh timetable data
    fresh_timetables = generate_multiple_timetables(num_versions=1)
    
    if fresh_timetables:
        timetable_data = fresh_timetables[0]
        consolidated = consolidate_timetables(timetable_data)
        
        return render_template("faculty_timetable_view.html", 
                             all_timetables={'Fresh Schedule': consolidated},
                             consolidated_schedule=consolidated,
                             assign_faculty_to_slot=assign_faculty_to_free_slot)
    else:
        flash('Failed to generate timetable', 'error')
        return redirect(url_for('main.dashboard'))


@main.route('/faculty-timetable-view')
@login_required
def faculty_timetable_view():
    """Enhanced timetable view optimized for faculty visualization"""
    # Get the latest published timetable first, then active timetables
    published_timetable = Timetable.query.filter_by(is_published=True).order_by(Timetable.published_at.desc()).first()
    
    if published_timetable:
        selected_timetable = published_timetable
    else:
        # Fall back to active timetables
        active_timetables = Timetable.query.filter_by(is_active=True).first()
        if active_timetables:
            selected_timetable = active_timetables
        else:
            # Generate a demo timetable if none exist
            from .scheduler import generate_multiple_timetables
            try:
                demo_timetables = generate_multiple_timetables(num_versions=1)
                if demo_timetables:
                    # Create a temporary timetable structure
                    all_timetables = demo_timetables[0]
                    faculty_classes = extract_faculty_classes(all_timetables, current_user.username) if current_user.is_faculty() else []
                    return render_template("faculty_timetable_view.html", 
                                         all_timetables=all_timetables,
                                         faculty_classes=faculty_classes,
                                         assign_faculty_to_slot=assign_faculty_to_free_slot)
            except Exception as e:
                print(f"Error generating demo timetable: {e}")
                flash('No timetables found. Please generate timetables first.', 'warning')
                return redirect(url_for('main.dashboard'))
    
    # Parse the timetable data
    import json
    timetable_data = json.loads(selected_timetable.data)
    
    # Pass the original classroom-based structure to the template
    all_timetables = timetable_data
    
    # Extract faculty classes for current user
    faculty_classes = extract_faculty_classes(all_timetables, current_user.username) if current_user.is_faculty() else []
    
    return render_template("faculty_timetable_view.html", 
                         all_timetables=all_timetables,
                         faculty_classes=faculty_classes,
                         assign_faculty_to_slot=assign_faculty_to_free_slot)

    
@main.route('/dashboard')
@login_required
def dashboard():
    classrooms = Classroom.query.all()
    faculties = Faculty.query.all()
    subjects = Subject.query.all()
    
    # Get active voting session info for scheduler
    active_timetables = []
    total_votes = 0
    if current_user.is_scheduler():
        active_timetables = Timetable.query.filter_by(is_active=True).order_by(Timetable.version).all()
        total_votes = sum(tt.vote_count for tt in active_timetables)
    
    # Get published timetable for all users
    published_timetable = Timetable.query.filter_by(is_published=True).order_by(Timetable.published_at.desc()).first()
    
    # Get faculty schedule if user is faculty
    faculty_schedule = None
    faculty_classes = []
    if current_user.is_faculty():
        faculty_schedule = get_faculty_schedule(current_user.username)
        faculty_classes = extract_faculty_classes(faculty_schedule, current_user.username)

    return render_template(
        'dashboard.html',
        classrooms=classrooms,
        faculties=faculties,
        subjects=subjects,
        current_user=current_user,
        active_timetables=active_timetables,
        total_votes=total_votes,
        faculty_schedule=faculty_schedule,
        faculty_classes=faculty_classes,
        published_timetable=published_timetable
    )


def get_faculty_schedule(faculty_username):
    """Get the schedule for a specific faculty member from active timetables"""
    # First try to get from active timetables (voting system)
    active_timetables = Timetable.query.filter_by(is_active=True).first()
    if active_timetables:
        try:
            timetable_data = json.loads(active_timetables.timetable_data)
            return timetable_data
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # If no active timetables, generate a fresh one for demo
    try:
        from .scheduler import generate_multiple_timetables
        demo_timetables = generate_multiple_timetables(num_versions=1)
        if demo_timetables:
            return demo_timetables[0]
    except Exception as e:
        print(f"Error generating demo timetable: {e}")
    
    return None


def extract_faculty_classes(timetable_data, faculty_username):
    """Extract classes assigned to a specific faculty member"""
    faculty_classes = []
    
    if not timetable_data:
        return faculty_classes
    
    # Get the actual faculty name from the database
    faculty_user = User.query.filter_by(username=faculty_username, role='faculty').first()
    if not faculty_user:
        return faculty_classes
    
    faculty_record = Faculty.query.filter_by(name=faculty_user.username).first()
    if not faculty_record:
        # Try to find by username directly
        faculty_record = Faculty.query.filter(Faculty.name.ilike(f'%{faculty_username}%')).first()
    
    # Get possible names to match against
    possible_names = [faculty_username]
    if faculty_record:
        possible_names.append(faculty_record.name)
    
    # Also try variations of the name
    if faculty_username.startswith('dr.'):
        possible_names.append(faculty_username.replace('dr.', 'Dr. ').strip())
    elif faculty_username.startswith('prof.'):
        possible_names.append(faculty_username.replace('prof.', 'Prof. ').strip())
    
    # Convert to title case
    possible_names.append(faculty_username.title())
    possible_names.append(faculty_username.replace('.', '. ').title())
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    slots = ["Slot 1", "Slot 2", "Slot 3", "Slot 4", "Slot 5", "Slot 6"]
    
    for classroom_name, classroom_schedule in timetable_data.items():
        for day in days:
            for slot in slots:
                if day in classroom_schedule and slot in classroom_schedule[day]:
                    classes = classroom_schedule[day][slot]
                    for class_info in classes:
                        if class_info:  # Not empty
                            parts = class_info.split('|')
                            if len(parts) >= 3:
                                subject, classroom, faculty = parts[0], parts[1], parts[2]
                                # Check if this faculty matches any of our possible names
                                if any(name.lower() == faculty.lower() for name in possible_names):
                                    faculty_classes.append({
                                        'subject': subject,
                                        'classroom': classroom,
                                        'day': day,
                                        'slot': slot,
                                        'time_display': f"{day} - {slot}"
                                    })
    
    return faculty_classes

@main.route('/faculty_credentials')
@login_required
@scheduler_required
def faculty_credentials():
    """View all faculty login credentials (Scheduler only)"""
    faculty_users = User.query.filter_by(role='faculty').all()
    return render_template('faculty_credentials.html', faculty_users=faculty_users)


@main.route('/save_parameters', methods=['POST'])
@login_required
@scheduler_required
def save_parameters():
    """Save timetable parameters"""
    try:
        # Get form data
        data = request.get_json() if request.is_json else request.form
        
        # Deactivate previous parameters
        TimetableParameters.query.update({'is_active': False})
        
        # Create new parameters
        params = TimetableParameters(
            num_classrooms=int(data.get('num_classrooms', 10)),
            num_batches=int(data.get('num_batches', 6)),
            max_classes_per_day=int(data.get('max_classes_per_day', 6)),
            total_subjects=int(data.get('total_subjects', 8)),
            default_classes_per_week=int(data.get('default_classes_per_week', 3)),
            total_faculties=int(data.get('total_faculties', 12)),
            avg_monthly_leaves=int(data.get('avg_monthly_leaves', 2)),
            fixed_time_slots=data.get('fixed_time_slots', ''),
            break_duration=int(data.get('break_duration', 15)),
            lunch_break_duration=int(data.get('lunch_break_duration', 60)),
            room_utilization_priority=int(data.get('room_utilization_priority', 8)),
            faculty_load_balance_priority=int(data.get('faculty_load_balance_priority', 7)),
            no_gaps_priority=int(data.get('no_gaps_priority', 6)),
            is_active=True
        )
        
        db.session.add(params)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Parameters saved successfully!'})
        else:
            flash('Parameters saved successfully!', 'success')
            return redirect(url_for('main.dashboard') + '#parameters')
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error saving parameters: {str(e)}'})
        else:
            flash(f'Error saving parameters: {str(e)}', 'error')
            return redirect(url_for('main.dashboard') + '#parameters')


@main.route('/reset_parameters', methods=['POST'])
@login_required
@scheduler_required
def reset_parameters():
    """Reset parameters to defaults"""
    try:
        # Deactivate previous parameters
        TimetableParameters.query.update({'is_active': False})
        
        # Create default parameters
        default_params = TimetableParameters(
            num_classrooms=10,
            num_batches=6,
            max_classes_per_day=6,
            total_subjects=8,
            default_classes_per_week=3,
            total_faculties=12,
            avg_monthly_leaves=2,
            fixed_time_slots='',
            break_duration=15,
            lunch_break_duration=60,
            room_utilization_priority=8,
            faculty_load_balance_priority=7,
            no_gaps_priority=6,
            is_active=True
        )
        
        db.session.add(default_params)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Parameters reset to defaults!'})
        else:
            flash('Parameters reset to defaults!', 'success')
            return redirect(url_for('main.dashboard') + '#parameters')
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error resetting parameters: {str(e)}'})
        else:
            flash(f'Error resetting parameters: {str(e)}', 'error')
            return redirect(url_for('main.dashboard') + '#parameters')


@main.route('/generate_optimized_timetable', methods=['POST'])
@login_required
@scheduler_required
def generate_optimized_timetable():
    """Generate optimized timetable using saved parameters"""
    try:
        # Get active parameters
        params = TimetableParameters.query.filter_by(is_active=True).first()
        if not params:
            # Create default parameters if none exist
            params = TimetableParameters()
            db.session.add(params)
            db.session.commit()
        
        # Get current data
        classrooms = Classroom.query.all()
        faculties = Faculty.query.all()
        subjects = Subject.query.all()
        
        if not classrooms or not faculties or not subjects:
            error_msg = "Please add classrooms, faculties, and subjects before generating timetables."
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('main.dashboard') + '#parameters')
        
        # Clear existing timetables
        Timetable.query.filter_by(is_active=True).delete()
        Vote.query.delete()
        db.session.commit()
        
        # Generate timetables using parameters
        timetables_data = generate_multiple_timetables(
            classrooms=classrooms,
            faculties=faculties, 
            subjects=subjects,
            parameters=params  # Pass parameters to generation function
        )
        
        # Save to database
        session_id = save_timetables_to_db(timetables_data)
        
        success_msg = f"Successfully generated {len(timetables_data)} optimized timetable options using your parameters!"
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': success_msg,
                'session_id': session_id,
                'timetable_count': len(timetables_data)
            })
        else:
            flash(success_msg, 'success')
            return redirect(url_for('main.voting_timetables'))
            
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error generating optimized timetable: {str(e)}'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('main.dashboard') + '#parameters')


@main.route('/get_parameters', methods=['GET'])
@login_required
@scheduler_required
def get_parameters():
    """Get current active parameters"""
    try:
        params = TimetableParameters.query.filter_by(is_active=True).first()
        if not params:
            # Return defaults if no parameters exist
            params_data = {
                'num_classrooms': Classroom.query.count(),
                'num_batches': 6,
                'max_classes_per_day': 6,
                'total_subjects': Subject.query.count(),
                'default_classes_per_week': 3,
                'total_faculties': Faculty.query.count(),
                'avg_monthly_leaves': 2,
                'fixed_time_slots': '',
                'break_duration': 15,
                'lunch_break_duration': 60,
                'room_utilization_priority': 8,
                'faculty_load_balance_priority': 7,
                'no_gaps_priority': 6
            }
        else:
            params_data = {
                'num_classrooms': params.num_classrooms,
                'num_batches': params.num_batches,
                'max_classes_per_day': params.max_classes_per_day,
                'total_subjects': params.total_subjects,
                'default_classes_per_week': params.default_classes_per_week,
                'total_faculties': params.total_faculties,
                'avg_monthly_leaves': params.avg_monthly_leaves,
                'fixed_time_slots': params.fixed_time_slots or '',
                'break_duration': params.break_duration,
                'lunch_break_duration': params.lunch_break_duration,
                'room_utilization_priority': params.room_utilization_priority,
                'faculty_load_balance_priority': params.faculty_load_balance_priority,
                'no_gaps_priority': params.no_gaps_priority
            }
        
        return jsonify({'success': True, 'parameters': params_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error getting parameters: {str(e)}'})

# Add Subject route

# create_missing_faculty_users.py
# Run this script to create user accounts for existing faculty who don't have login accounts

from app import create_app, db
from app.models import User, Faculty
import re

def create_missing_faculty_users():
    app = create_app()
    
    with app.app_context():
        print("Creating user accounts for faculty without login credentials...")
        
        # Find faculty members without user accounts
        faculty_without_users = []
        all_faculty = Faculty.query.all()
        
        for faculty in all_faculty:
            existing_user = User.query.filter_by(faculty_id=faculty.id).first()
            if not existing_user:
                faculty_without_users.append(faculty)
        
        if not faculty_without_users:
            print("All faculty members already have user accounts!")
            return
        
        print(f"Found {len(faculty_without_users)} faculty members without user accounts:")
        
        for faculty in faculty_without_users:
            # Create username from faculty name
            username = faculty.name.lower().replace(' ', '.').replace('dr.', 'dr').replace('prof.', 'prof')
            # Remove any special characters except dots
            username = re.sub(r'[^a-z0-9.]', '', username)
            
            # Check if username already exists, add number if needed
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user account
            new_user = User(
                username=username,
                password='faculty123',  # Default password
                role='faculty',
                faculty_id=faculty.id
            )
            db.session.add(new_user)
            print(f"Created account for {faculty.name}: username={username}, password=faculty123")
        
        db.session.commit()
        print(f"\nSuccessfully created {len(faculty_without_users)} user accounts!")
        
        # Show all faculty login credentials
        print("\n=== ALL FACULTY LOGIN CREDENTIALS ===")
        all_faculty_users = User.query.filter_by(role='faculty').all()
        for user in all_faculty_users:
            faculty_name = user.faculty.name if user.faculty else 'Unknown'
            print(f"Faculty: {faculty_name} -> Username: {user.username}, Password: {user.password}")

if __name__ == '__main__':
    create_missing_faculty_users()
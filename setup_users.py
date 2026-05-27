# setup_users.py
# Run this script to create test users for the application

from app import create_app, db
from app.models import User, Faculty

def setup_test_users():
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if users already exist
        if User.query.count() > 0:
            print("Users already exist. Skipping user creation.")
            return
        
        # Create scheduler/admin user
        scheduler = User(
            username='admin',
            password='admin123',  # In production, use proper password hashing
            role='scheduler'
        )
        db.session.add(scheduler)
        
        # Create some faculty users
        # First, let's create some faculty records
        faculty1 = Faculty(name='Dr. Smith', subject='Mathematics')
        faculty2 = Faculty(name='Prof. Johnson', subject='Physics')
        faculty3 = Faculty(name='Dr. Williams', subject='Chemistry')
        
        db.session.add(faculty1)
        db.session.add(faculty2)
        db.session.add(faculty3)
        db.session.commit()  # Commit to get IDs
        
        # Now create user accounts for faculty
        faculty_user1 = User(
            username='dr.smith',
            password='faculty123',
            role='faculty',
            faculty_id=faculty1.id
        )
        
        faculty_user2 = User(
            username='prof.johnson',
            password='faculty123',
            role='faculty',
            faculty_id=faculty2.id
        )
        
        faculty_user3 = User(
            username='dr.williams',
            password='faculty123',
            role='faculty',
            faculty_id=faculty3.id
        )
        
        db.session.add(faculty_user1)
        db.session.add(faculty_user2)
        db.session.add(faculty_user3)
        
        db.session.commit()
        
        print("Test users created successfully!")
        print("\nScheduler Login:")
        print("Username: admin")
        print("Password: admin123")
        print("\nFaculty Logins:")
        print("Username: dr.smith, Password: faculty123")
        print("Username: prof.johnson, Password: faculty123")
        print("Username: dr.williams, Password: faculty123")

if __name__ == '__main__':
    setup_test_users()
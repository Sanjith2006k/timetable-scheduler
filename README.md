# Class Scheduler with Voting System

This application now supports role-based access with voting on multiple timetable options.

## Features

### Role-Based Access

- **Scheduler/Admin**: Can manage classrooms, faculty, subjects, and generate timetables
- **Faculty**: Can view and vote on timetable options

### Voting System

- Scheduler can generate 3 different timetable variations
- Faculty members can vote on their preferred timetable
- Real-time vote counting
- One vote per faculty member per voting session
- Scheduler can end voting and see results

## Setup Instructions

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Test Users**

   ```bash
   python setup_users.py
   ```

3. **Run the Application**
   ```bash
   python run.py
   ```

## Default Login Credentials

### Scheduler/Admin

- Username: `admin`
- Password: `admin123`

### Faculty Members

- Username: `dr.smith`, Password: `faculty123`
- Username: `prof.johnson`, Password: `faculty123`
- Username: `dr.williams`, Password: `faculty123`

## How to Use

### For Schedulers:

1. Login with admin credentials
2. Add classrooms, faculty, and subjects as needed
3. Click "Generate 3 Timetables" to create voting options
4. Monitor voting progress in the dashboard
5. End voting session when ready

### For Faculty:

1. Login with faculty credentials
2. Navigate to "Vote on Timetables"
3. Review the 3 timetable options
4. Vote for your preferred option
5. You can change your vote before the session ends

## New Routes

- `/generate_timetables` - Generate 3 timetable options (Scheduler only)
- `/voting_timetables` - View and vote on timetables
- `/vote/<id>` - Cast a vote (Faculty only)
- `/end_voting` - End voting session (Scheduler only)

## Database Changes

- Added `role` field to User model
- Added `faculty_id` link in User model
- New `Timetable` model for storing multiple versions
- New `Vote` model for tracking faculty votes
- Added session management for voting rounds

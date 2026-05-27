#!/usr/bin/env python3
"""Test script to check voting functionality"""
import sys
sys.path.append('.')
from app import create_app

app = create_app()

# Test route
with app.test_client() as client:
    print("Testing voting route...")
    
    # Test without login (should redirect to login)
    response = client.get('/voting_timetables')
    print(f"Without login: Status {response.status_code}")
    
    # Test with admin login
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    
    print(f"Login response: Status {response.status_code}")
    
    # Now test voting page
    response = client.get('/voting_timetables')
    print(f"With login: Status {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Voting page loads successfully!")
        # Check if page contains expected content
        content = response.data.decode('utf-8')
        if 'Timetable Voting' in content:
            print("✅ Page contains voting title")
        if 'Timetable Option' in content:
            print("✅ Page contains timetable options")
        else:
            print("⚠️ No timetable options found in page")
    else:
        print(f"❌ Error loading voting page: {response.status_code}")
        print(f"Response: {response.data.decode('utf-8')[:200]}...")
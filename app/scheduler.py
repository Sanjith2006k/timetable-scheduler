# app/scheduler.py
from ortools.sat.python import cp_model
from .models import Classroom, Faculty, Subject, Timetable
from . import db
import json
import uuid
import random

def generate_timetable():
    """Generate a single timetable - keeping original function for backward compatibility"""
    timetables = generate_multiple_timetables(num_versions=1)
    return timetables[0] if timetables else None

def analyze_workload_balance(timetables):
    """Analyze workload distribution among faculty for debugging"""
    faculty_workload = {}
    faculty_subject_hours = {}
    
    for room_name, timetable in timetables.items():
        for day in timetable:
            for slot in timetable[day]:
                for entry in timetable[day][slot]:
                    if entry:  # Not empty slot
                        parts = entry.split('|')
                        if len(parts) >= 3:
                            subject, classroom, faculty = parts[0], parts[1], parts[2]
                            
                            # Count total hours per faculty
                            faculty_workload[faculty] = faculty_workload.get(faculty, 0) + 1
                            
                            # Count hours per subject per faculty
                            key = f"{faculty}_{subject}"
                            faculty_subject_hours[key] = faculty_subject_hours.get(key, 0) + 1
    
    print("\n=== WORKLOAD ANALYSIS ===")
    print("Faculty Total Hours:")
    for faculty, hours in sorted(faculty_workload.items()):
        print(f"  {faculty}: {hours} hours")
    
    print("\nSubject Distribution per Faculty:")
    subject_faculty_map = {}
    for key, hours in faculty_subject_hours.items():
        faculty, subject = key.rsplit('_', 1)
        if subject not in subject_faculty_map:
            subject_faculty_map[subject] = {}
        subject_faculty_map[subject][faculty] = hours
    
    for subject, faculty_hours in subject_faculty_map.items():
        if len(faculty_hours) > 1:  # Multiple faculty teaching same subject
            print(f"  {subject}:")
            total_hours = sum(faculty_hours.values())
            for faculty, hours in faculty_hours.items():
                percentage = (hours / total_hours) * 100
                print(f"    {faculty}: {hours} hours ({percentage:.1f}%)")
    
    return faculty_workload, faculty_subject_hours


def generate_multiple_timetables(num_versions=3):
    """Generate multiple timetable variations with balanced workload"""
    all_versions = []
    
    for version in range(num_versions):
        # Add some randomization to create different solutions
        random.seed(42 + version * 10)  # Different seed for each version
        
        print(f"\nGenerating Version {version + 1}...")
        timetable = _generate_single_timetable_version(version + 1)
        if timetable:
            # Analyze workload for this version
            print(f"Analyzing workload for Version {version + 1}...")
            faculty_workload, faculty_subject_hours = analyze_workload_balance(timetable)
            all_versions.append(timetable)
            print(f"Version {version + 1} generated successfully!")
        else:
            print(f"Failed to generate Version {version + 1}")
    
    return all_versions


def _generate_single_timetable_version(version_num):
    """Generate a single timetable version with balanced workload and consistent faculty assignments"""
    model = cp_model.CpModel()

    classrooms = Classroom.query.all()
    subjects = Subject.query.all()
    faculties = Faculty.query.all()

    classroom_ids = [c.id for c in classrooms]
    subject_ids = [s.id for s in subjects]
    faculty_ids = [f.id for f in faculties]

    # Create improved subject-faculty mapping with workload balance
    subject_faculty_map = {}
    faculty_id_name_map = {}
    faculty_subjects = {}  # Track which subjects each faculty teaches
    
    for f in faculties:
        faculty_id_name_map[f.id] = f.name
        subject_faculty_map.setdefault(f.subject, []).append(f.id)
        faculty_subjects[f.id] = f.subject

    num_days = 5
    slots_per_day = 6
    num_slots = num_days * slots_per_day

    assign = {}
    faculty_assign = {}
    
    # Track faculty workload variables
    faculty_workload = {}
    for f_id in faculty_ids:
        faculty_workload[f_id] = model.NewIntVar(0, num_slots, f'faculty_{f_id}_workload')

    # Decision variables
    for s in subject_ids:
        subject_name = Subject.query.get(s).name
        faculty_list = subject_faculty_map.get(subject_name, [])
        for slot in range(num_slots):
            for room in classroom_ids:
                assign[(s, slot, room)] = model.NewBoolVar(f'subject{s}_slot{slot}_room{room}')
                for f_id in faculty_list:
                    faculty_assign[(s, slot, room, f_id)] = model.NewBoolVar(
                        f's_assign{s}_slot{slot}_room{room}_faculty{f_id}'
                    )

    # Constraint: Each subject must have required hours per week
    for subject in subjects:
        for room in classroom_ids:
            model.Add(
                sum(assign[(subject.id, slot, room)] for slot in range(num_slots))
                == subject.hours_per_week
            )

    # Constraint: Only one class per room per slot
    for room in classroom_ids:
        for slot in range(num_slots):
            model.Add(sum(assign[(s, slot, room)] for s in subject_ids) <= 1)

    # Constraint: If subject is assigned, exactly one faculty must teach it
    for s in subject_ids:
        subject_name = Subject.query.get(s).name
        faculty_list = subject_faculty_map.get(subject_name, [])
        if not faculty_list:
            continue
        for slot in range(num_slots):
            for room in classroom_ids:
                model.Add(
                    sum(faculty_assign[(s, slot, room, f_id)] for f_id in faculty_list)
                    == assign[(s, slot, room)]
                )

    # Constraint: Faculty can only be in one place at a time
    for f_id in faculty_ids:
        for slot in range(num_slots):
            model.Add(
                sum(
                    faculty_assign[(s, slot, room, f_id)]
                    for s in subject_ids
                    for room in classroom_ids
                    if (s, slot, room, f_id) in faculty_assign
                )
                <= 1
            )

    # Calculate faculty workload
    for f_id in faculty_ids:
        model.Add(
            faculty_workload[f_id] == sum(
                faculty_assign[(s, slot, room, f_id)]
                for s in subject_ids
                for slot in range(num_slots)
                for room in classroom_ids
                if (s, slot, room, f_id) in faculty_assign
            )
        )

    # NEW: Balanced workload constraints
    # Ensure workload is distributed fairly among faculty teaching the same subject
    for subject_name, faculty_list in subject_faculty_map.items():
        if len(faculty_list) > 1:  # Multiple faculty for same subject
            # Calculate ideal workload per faculty for this subject
            subject_obj = Subject.query.filter_by(name=subject_name).first()
            if subject_obj:
                total_hours = subject_obj.hours_per_week * len(classroom_ids)
                ideal_per_faculty = total_hours // len(faculty_list)
                remainder = total_hours % len(faculty_list)
                
                # Ensure balanced distribution
                for i, f_id in enumerate(faculty_list):
                    subject_workload = sum(
                        faculty_assign[(subject_obj.id, slot, room, f_id)]
                        for slot in range(num_slots)
                        for room in classroom_ids
                        if (subject_obj.id, slot, room, f_id) in faculty_assign
                    )
                    
                    min_workload = ideal_per_faculty
                    max_workload = ideal_per_faculty + (1 if i < remainder else 0)
                    
                    model.Add(subject_workload >= min_workload)
                    model.Add(subject_workload <= max_workload)

    # NEW: Simplified consistency constraints - focus on same faculty for same subject
    for subject_name, faculty_list in subject_faculty_map.items():
        if len(faculty_list) > 1:
            subject_obj = Subject.query.filter_by(name=subject_name).first()
            if subject_obj:
                # Try to ensure each faculty gets consistent assignments within the same day
                for day in range(num_days):
                    for f_id in faculty_list:
                        daily_assignments = []
                        for slot_in_day in range(slots_per_day):
                            slot = day * slots_per_day + slot_in_day
                            for room in classroom_ids:
                                if (subject_obj.id, slot, room, f_id) in faculty_assign:
                                    daily_assignments.append(faculty_assign[(subject_obj.id, slot, room, f_id)])
                        
                        # If a faculty teaches this subject on a day, prefer consecutive slots
                        if len(daily_assignments) > 1:
                            for i in range(len(daily_assignments) - 1):
                                # Soft constraint: if teaching in slot i, prefer teaching in slot i+1
                                consistency_bonus = model.NewBoolVar(f'bonus_{f_id}_day{day}_consec{i}')
                                model.Add(consistency_bonus <= daily_assignments[i])
                                model.Add(consistency_bonus <= daily_assignments[i+1])

    # NEW: Simplified faculty switch minimization
    faculty_day_switches = []
    for f_id in faculty_ids:
        for day in range(num_days):
            # Count teaching slots per day
            daily_teaching_slots = []
            for slot_in_day in range(slots_per_day):
                slot = day * slots_per_day + slot_in_day
                teaching_this_slot = sum(
                    faculty_assign[(s, slot, room, f_id)]
                    for s in subject_ids
                    for room in classroom_ids
                    if (s, slot, room, f_id) in faculty_assign
                )
                daily_teaching_slots.append(teaching_this_slot)
            
            # Add penalty for non-consecutive teaching (simplified)
            for i in range(slots_per_day - 1):
                gap_penalty = model.NewBoolVar(f'gap_{f_id}_day{day}_slot{i}')
                # Penalty if teaching in slot i and i+2 but not i+1
                if i < slots_per_day - 2:
                    model.Add(gap_penalty >= daily_teaching_slots[i] + daily_teaching_slots[i+2] - daily_teaching_slots[i+1] - 1)
                    faculty_day_switches.append(gap_penalty)

    # Add variation-specific constraints for different versions
    if version_num > 1:
        preference_vars = []
        for slot in range(0, num_slots, 6):  # Start of each day
            for room_idx, room in enumerate(classroom_ids):
                if (room_idx + version_num) % len(classroom_ids) == 0:
                    for s in subject_ids[:2]:
                        if (s, slot, room) in assign:
                            pref_var = model.NewBoolVar(f'pref_v{version_num}_s{s}_slot{slot}_room{room}')
                            model.Add(pref_var == assign[(s, slot, room)])
                            preference_vars.append(pref_var)
        
        if preference_vars:
            # Multi-objective: balance preferences with workload balance
            if len(faculty_ids) > 1:
                workload_deviations = []
                for i, f1_id in enumerate(faculty_ids):
                    for j, f2_id in enumerate(faculty_ids[i+1:], i+1):
                        deviation = model.NewIntVar(0, num_slots, f'deviation_v{version_num}_{f1_id}_{f2_id}')
                        model.AddAbsEquality(deviation, faculty_workload[f1_id] - faculty_workload[f2_id])
                        workload_deviations.append(deviation)
                
                # Minimize: workload variance + faculty switches - preferences
                model.Minimize(
                    sum(workload_deviations) + 
                    sum(faculty_day_switches) - 
                    sum(preference_vars)
                )
            else:
                model.Maximize(sum(preference_vars))
    else:
        # For version 1, focus on workload balance and minimize switches
        if len(faculty_ids) > 1:
            # Minimize workload variance and faculty switches
            # Create individual deviation variables for each faculty pair
            workload_deviations = []
            for i, f1_id in enumerate(faculty_ids):
                for j, f2_id in enumerate(faculty_ids[i+1:], i+1):
                    deviation = model.NewIntVar(0, num_slots, f'deviation_{f1_id}_{f2_id}')
                    model.AddAbsEquality(deviation, faculty_workload[f1_id] - faculty_workload[f2_id])
                    workload_deviations.append(deviation)
            
            if workload_deviations:
                model.Minimize(sum(workload_deviations) + sum(faculty_day_switches))
            else:
                model.Minimize(sum(faculty_day_switches))

    # Solve with improved parameters
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 42 + version_num * 10
    solver.parameters.max_time_in_seconds = 20.0  # Reduced time for faster testing
    solver.parameters.num_search_workers = 2  # Reduced workers
    
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Build timetable per classroom with improved faculty assignments
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    slots = ["Slot 1", "Slot 2", "Slot 3", "Slot 4", "Slot 5", "Slot 6"]

    all_timetables = {}

    for room in classrooms:
        timetable = {day: {slot: [] for slot in slots} for day in days}
        for slot in range(num_slots):
            day_name = days[slot // slots_per_day]
            slot_name = slots[slot % slots_per_day]

            for s in subject_ids:
                if solver.Value(assign[(s, slot, room.id)]) == 1:
                    subject_name = Subject.query.get(s).name
                    faculty_list = subject_faculty_map.get(subject_name, [])
                    assigned_faculty = None
                    for f_id in faculty_list:
                        if solver.Value(faculty_assign[(s, slot, room.id, f_id)]) == 1:
                            assigned_faculty = faculty_id_name_map[f_id]
                            break
                    if not assigned_faculty:
                        assigned_faculty = "TBD"

                    timetable[day_name][slot_name].append(
                        f"{subject_name}|{room.name}|{assigned_faculty}"
                    )
        all_timetables[room.name] = timetable

    return all_timetables

def save_timetables_to_db(timetables_list):
    """Save multiple timetables to database for voting"""
    session_id = str(uuid.uuid4())
    
    # Mark previous sessions as inactive
    Timetable.query.filter_by(is_active=True).update({'is_active': False})
    
    saved_timetables = []
    for i, timetable_data in enumerate(timetables_list):
        timetable = Timetable(
            name=f"Timetable Option {i+1}",
            data=json.dumps(timetable_data),
            version=i+1,
            session_id=session_id,
            is_active=True,
            vote_count=0
        )
        db.session.add(timetable)
        saved_timetables.append(timetable)
    
    db.session.commit()
    return saved_timetables, session_id

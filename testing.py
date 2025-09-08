# testing.py
# This script runs a full, end-to-end test of the entire application workflow.

from main import app  # Import the compiled LangGraph application
import uuid
import os
from typing import Any, Dict

# --- HELPER FUNCTION ---
def run_step(config: Dict, step_name: str, inputs: Dict | None = None) -> Dict:
    """
    A helper to run a step in the graph, print the output, and return the final state.
    It now uses app.get_state() to ensure it gets the full, final state.
    """
    print(f"\n{'='*20}\n▶️  STEP: {step_name}\n{'='*20}")
    
    # Use a placeholder for the initial run which has no input
    run_input = inputs if inputs is not None else {"user_data": {}}
    
    # Run the stream to completion. We don't need the intermediate steps,
    # just the side effect of the state being updated.
    for _ in app.stream(run_input, config=config):
        pass

    # ✅ FIX: After the stream is done, explicitly get the final state for the session.
    final_state_snapshot = app.get_state(config)
    
    # The final state is stored in the 'values' attribute of the snapshot
    response = final_state_snapshot.values
    
    print(f"✅ RESPONSE: {response.get('message', 'No message returned.')}")
    return response

# --- MAIN TEST FUNCTION ---
def run_full_test():
    """Orchestrates the entire test from admin to student."""
    print("🚀 STARTING FULL SYSTEM TEST 🚀")

    # --- 1. SETUP ---
    # This config will be used for the entire "session"
    session_id = str(uuid.uuid4())
    config: dict[str, Any] = {
        "recursion_limit": 150, # Increased for a long chain of events
        "configurable": {"thread_id": session_id}
    }

    # --- DUMMY DATA ---
    # IMPORTANT: Customize these credentials to match your created admin
    ADMIN_CREDENTIALS = {"email": "admin@example.com", "password": "abcd1234"}
    
    COLLEGE_DATA = {
        "name": "LangGraph University", "principal_name": "Dr. Sam Altman",
        "principal_age": 38, "phone_no": "1234567890", "email": "principal.sam@lgu.edu"
    }
    TEACHER_DATA = {
        "name": "Prof. Geoffrey Hinton", "age": 76, "address": "123 Neural Net Avenue",
        "phone_no": "9876543210", "email": "prof.hinton@lgu.edu", "assigned_class": "Deep Learning 101"
    }
    STUDENT_DATA = {
        "name": "Alex Student", "age": 20, "address": "456 Backprop Boulevard",
        "phone_no": "5555555555", "email": "alex.student@lgu.edu"
    }

    # --- 2. ADMIN FLOW: Create a College ---
    # Login as Admin
    admin_login_inputs = {"user_data": ADMIN_CREDENTIALS}
    response = run_step(config, "Admin Login", admin_login_inputs)
    if response.get("current_role") != "admin":
        print("❌ TEST FAILED: Admin login was unsuccessful.")
        return

    # Add College
    add_college_inputs = {"action": "add_college", "user_data": COLLEGE_DATA}
    response = run_step(config, "Admin Adds College", add_college_inputs)
    try:
        # Extract the temporary password for the new college principal
        college_password = response['message'].split("password: ")[1]
        college_creds = {"email": COLLEGE_DATA["email"], "password": college_password}
    except (KeyError, IndexError):
        print("❌ TEST FAILED: Could not extract college principal's password from response.")
        return

    # --- 3. COLLEGE FLOW: Create a Teacher ---
    # Login as College Principal
    college_login_inputs = {"user_data": college_creds}
    response = run_step(config, "College Principal Login", college_login_inputs)
    if response.get("current_role") != "college":
        print("❌ TEST FAILED: College Principal login was unsuccessful.")
        return
        
    # Add Teacher
    add_teacher_inputs = {"action": "add_teacher", "user_data": TEACHER_DATA}
    response = run_step(config, "College Adds Teacher", add_teacher_inputs)
    try:
        teacher_password = response['message'].split("password: ")[1]
        teacher_creds = {"email": TEACHER_DATA["email"], "password": teacher_password}
    except (KeyError, IndexError):
        print("❌ TEST FAILED: Could not extract teacher's password from response.")
        return

    # --- 4. TEACHER FLOW: Create Student, Generate & Send Quiz ---
    # Login as Teacher
    teacher_login_inputs = {"user_data": teacher_creds}
    response = run_step(config, "Teacher Login", teacher_login_inputs)
    if response.get("current_role") != "teacher":
        print("❌ TEST FAILED: Teacher login was unsuccessful.")
        return

    # Add Student
    add_student_inputs = {"action": "add_student", "user_data": STUDENT_DATA}
    response = run_step(config, "Teacher Adds Student", add_student_inputs)
    try:
        student_password = response['message'].split("password: ")[1]
        student_creds = {"email": STUDENT_DATA["email"], "password": student_password}
    except (KeyError, IndexError):
        print("❌ TEST FAILED: Could not extract student's password from response.")
        return
        
    # Generate Quiz
    # Create a dummy PDF file for the test
    PDF_PATH = "test_photosynthesis.pdf"
    with open(PDF_PATH, "w") as f:
        f.write("Photosynthesis is the process used by plants, algae, and certain bacteria to harness energy from sunlight and turn it into chemical energy.")
    
    generate_quiz_inputs = {
        "action": "generate_assignment",
        "user_data": {
            "pdf_file_path": PDF_PATH, "topic": "Photosynthesis",
            "num_mcq": 1, "num_short": 1, "num_long": 0
        }
    }
    response = run_step(config, "Teacher Generates Quiz", generate_quiz_inputs)
    try:
        assignment_id = response['message'].split("ID: ")[1]
    except (KeyError, IndexError):
        print("❌ TEST FAILED: Could not extract assignment ID from response.")
        return

    # Send Quiz
    send_quiz_inputs = {
        "action": "send_assignment",
        "user_data": {"assignment_id": assignment_id, "class_ids": [TEACHER_DATA["assigned_class"]]}
    }
    run_step(config, "Teacher Sends Quiz", send_quiz_inputs)

    # --- 5. STUDENT FLOW: Submit Assignment ---
    # Login as Student
    student_login_inputs = {"user_data": student_creds}
    response = run_step(config, "Student Login", student_login_inputs)
    if response.get("current_role") != "student":
        print("❌ TEST FAILED: Student login was unsuccessful.")
        return
        
    # Submit Assignment
    student_answers = {
        "mcq_answers": [{"question_id": 0, "answer": "A"}], # Dummy answers
        "short_answers": [{"question_id": 0, "answer": "It is how plants make food from sunlight."}]
    }
    submit_assignment_inputs = {
        "action": "submit_assignment",
        "user_data": {"assignment_id": assignment_id, "answers": student_answers}
    }
    # The final response will contain the LLM's evaluation of the answers
    run_step(config, "Student Submits Assignment", submit_assignment_inputs)
    
    # Clean up the dummy PDF
    os.remove(PDF_PATH)
    
    print("\n🎉🎉🎉 FULL SYSTEM TEST COMPLETED SUCCESSFULLY! 🎉🎉🎉")

if __name__ == "__main__":
    run_full_test()


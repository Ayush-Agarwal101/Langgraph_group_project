# file name: testing.py

from main import app  # Import the compiled LangGraph application
import uuid
import os
from typing import Any, Dict


# --- HELPER FUNCTION ---
def run_step(config: Dict, step_name: str, inputs: Dict | None = None) -> Dict:
    """
    Run a step in the graph, print the output, and return the final state.
    It now reads the 'response' field from AppState.
    """
    print(f"\n{'='*20}\n▶️  STEP: {step_name}\n{'='*20}")

    run_input = inputs if inputs is not None else {"user_data": {}}

    # Run the step
    for _ in app.stream(run_input, config=config):
        pass

    # Get final state snapshot
    final_state_snapshot = app.get_state(config)
    response = final_state_snapshot.values

    # Prefer 'response' field
    message = response.get("response") or response.get("message", "No message returned.")
    print(f"✅ RESPONSE: {message}")

    return response


# --- MAIN TEST FUNCTION ---
def run_full_test():
    """Full test of the system workflow."""
    print("🚀 STARTING FULL SYSTEM TEST 🚀")

    # --- 1. SETUP ---
    session_id = str(uuid.uuid4())
    config = {
    "configurable": {
        "thread_id": session_id,   
        "recursion_limit": 150    
    }
}


    # Dummy data
    ADMIN_EMAIL= "admin@example.com"
    ADMIN_PASSWORD = "abcd1234"

    COLLEGE_DATA = {
        "name": "LangGraph University",
        "principal_name": "Dr. Sam Altman",
        "principal_age": 38,
        "phone_no": "1234567890",
        "email": "principal.sam@lgu.edu",
    }
    TEACHER_DATA = {
        "name": "Prof. Geoffrey Hinton",
        "age": 76,
        "address": "123 Neural Net Avenue",
        "phone_no": "9876543210",
        "email": "prof.hinton@lgu.edu",
        "assigned_class": "Deep Learning 101",
    }
    STUDENT_DATA = {
        "name": "Alex Student",
        "age": 20,
        "address": "456 Backprop Boulevard",
        "phone_no": "5555555555",
        "email": "alex.student@lgu.edu",
    }

    # --- 2. ADMIN FLOW ---
    response = run_step(config, "login", {"user_input": ADMIN_EMAIL, "password": ADMIN_PASSWORD})

    if response.get("current_role") != "admin":
        print("❌ TEST FAILED: Admin login unsuccessful.")
        return

    response = run_step(config, "Admin Adds College", {"action": "add_college", "user_data": COLLEGE_DATA})

    # --- 3. COLLEGE FLOW ---
    # (etc… continue with teacher/student like before)


if __name__ == "__main__":
    run_full_test()
# langgraph_nodes.py

from typing import Dict
from passlib.hash import bcrypt

# --- Shared AppState type ---
AppState = Dict[str, any]


# ==========================
# LOGIN / LOGOUT NODES
# ==========================

def login_node(state: AppState) -> AppState:
    """
    Handles login and sets role.
    """
    user_input = state.get("user_input", "").strip().lower()

    # Example fake login
    if user_input == "admin":
        state["current_role"] = "admin"
        state["message"] = "✅ Logged in as Admin"
    elif user_input == "college":
        state["current_role"] = "college"
        state["message"] = "✅ Logged in as College"
    elif user_input == "teacher":
        state["current_role"] = "teacher"
        state["message"] = "✅ Logged in as Teacher"
    elif user_input == "student":
        state["current_role"] = "student"
        state["message"] = "✅ Logged in as Student"
    else:
        state["current_role"] = "unauthenticated"
        state["message"] = "❌ Login failed. Try again."

    return state


def logout_node(state: AppState) -> AppState:
    """
    Logs out the current user.
    """
    state["current_role"] = "unauthenticated"
    state["action"] = "END_OF_TURN"
    state["message"] = "✅ Logged out successfully."
    return state


# ==========================
# ADMIN MENU
# ==========================

def admin_menu_node(state: AppState) -> AppState:
    """
    Admin menu: stops until user chooses an action.
    """
    user_input = state.get("user_input", "").strip().lower()

    valid_actions = {
        "add_college": "add_college",
        "remove_college": "remove_college",
        "list_colleges": "list_colleges",
        "logout": "logout",
    }

    if user_input in valid_actions:
        state["action"] = valid_actions[user_input]
    else:
        state["action"] = "END_OF_TURN"  # ✅ stop recursion

    state["message"] = "ADMIN MENU | Actions: [add_college, remove_college, list_colleges, logout]"
    return state


# ==========================
# COLLEGE MENU
# ==========================

def college_menu_node(state: AppState) -> AppState:
    """
    College menu: stops until user chooses an action.
    """
    user_input = state.get("user_input", "").strip().lower()

    valid_actions = {
        "add_teacher": "add_teacher",
        "remove_teacher": "remove_teacher",
        "list_teachers": "list_teachers",
        "logout": "logout",
    }

    if user_input in valid_actions:
        state["action"] = valid_actions[user_input]
    else:
        state["action"] = "END_OF_TURN"

    state["message"] = "COLLEGE MENU | Actions: [add_teacher, remove_teacher, list_teachers, logout]"
    return state


# ==========================
# TEACHER MENU
# ==========================

def teacher_menu_node(state: AppState) -> AppState:
    """
    Teacher menu: stops until user chooses an action.
    """
    user_input = state.get("user_input", "").strip().lower()

    valid_actions = {
        "add_student": "add_student",
        "generate_assignment": "generate_assignment",
        "send_assignment": "send_assignment",
        "logout": "logout",
    }

    if user_input in valid_actions:
        state["action"] = valid_actions[user_input]
    else:
        state["action"] = "END_OF_TURN"

    state["message"] = "TEACHER MENU | Actions: [add_student, generate_assignment, send_assignment, logout]"
    return state


# ==========================
# STUDENT MENU
# ==========================

def student_menu_node(state: AppState) -> AppState:
    """
    Student menu: stops until user chooses an action.
    """
    user_input = state.get("user_input", "").strip().lower()

    valid_actions = {
        "get_assignments": "get_assignments",
        "submit_assignment": "submit_assignment",
        "summarize_pdf": "summarize_pdf",
        "logout": "logout",
    }

    if user_input in valid_actions:
        state["action"] = valid_actions[user_input]
    else:
        state["action"] = "END_OF_TURN"

    state["message"] = "STUDENT MENU | Actions: [get_assignments, submit_assignment, summarize_pdf, logout]"
    return state


# ==========================
# PLACEHOLDER ACTION NODES
# ==========================

def add_college_node(state: AppState) -> AppState:
    state["message"] = "✅ College added successfully!"
    return state

def remove_college_node(state: AppState) -> AppState:
    state["message"] = "✅ College removed successfully!"
    return state

def list_colleges_node(state: AppState) -> AppState:
    state["message"] = "📋 Colleges: [College1, College2]"
    return state


def add_teacher_node(state: AppState) -> AppState:
    state["message"] = "✅ Teacher added successfully!"
    return state

def remove_teacher_node(state: AppState) -> AppState:
    state["message"] = "✅ Teacher removed successfully!"
    return state

def list_teachers_node(state: AppState) -> AppState:
    state["message"] = "📋 Teachers: [Teacher1, Teacher2]"
    return state


def add_student_node(state: AppState) -> AppState:
    state["message"] = "✅ Student added successfully!"
    return state

def generate_assignment_node(state: AppState) -> AppState:
    state["message"] = "📝 Assignment generated!"
    return state

def send_assignment_node(state: AppState) -> AppState:
    state["message"] = "📩 Assignment sent to students!"
    return state


def get_assignments_node(state: AppState) -> AppState:
    state["message"] = "📚 You have 2 pending assignments."
    return state

def submit_assignment_node(state: AppState) -> AppState:
    state["message"] = "✅ Assignment submitted!"
    return state

def summarize_pdf_node(state: AppState) -> AppState:
    state["message"] = "📄 PDF summarized successfully!"
    return state

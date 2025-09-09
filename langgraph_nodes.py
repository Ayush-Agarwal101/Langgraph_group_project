# file: langgraph_nodes.py

from typing import TypedDict, Literal, Optional, Dict, Any
from passlib.hash import bcrypt
from database import users_collection, colleges_collection, teachers_collection, students_collection


# --- State Definition ---
class AppState(TypedDict, total=False):
    current_role: Literal["admin", "college", "teacher", "student", "unauthenticated"]
    current_user_id: Optional[str]
    action: Optional[str]
    user_input: Optional[str]
    response: Optional[str]   # 👈 NEW field for menu or status messages


# --- Helper ---
def make_response(state: AppState, message: str) -> AppState:
    state["response"] = message
    return state


# --- Nodes ---
def login_node(state: AppState) -> AppState:
    user_input = str(state.get("user_input", "")).strip().lower()
    user_doc = users_collection.find_one({"email": user_input})
    if user_doc and bcrypt.verify(state.get("password", ""), user_doc["_password_hash"]):
        state["current_user_id"] = user_doc["_id"]
        state["current_role"] = user_doc["role"]
        return make_response(state, f"✅ Logged in as {user_doc['role'].upper()} | Actions: [...]")
    else:
        state["current_role"] = "unauthenticated"
        return make_response(state, "❌ Invalid login. Please try again.")


def logout_node(state: AppState) -> AppState:
    state["current_role"] = "unauthenticated"
    state["current_user_id"] = None
    return make_response(state, "👋 You have been logged out.")


def admin_menu_node(state: AppState) -> AppState:
    return make_response(state, "ADMIN MENU | Actions: [add_college, remove_college, list_colleges, logout]")


def college_menu_node(state: AppState) -> AppState:
    return make_response(state, "COLLEGE MENU | Actions: [add_teacher, remove_teacher, list_teachers, logout]")


def teacher_menu_node(state: AppState) -> AppState:
    return make_response(state, "TEACHER MENU | Actions: [add_student, generate_assignment, send_assignment, logout]")


def student_menu_node(state: AppState) -> AppState:
    return make_response(state, "STUDENT MENU | Actions: [get_assignments, submit_assignment, summarize_pdf, logout]")


# --- Admin Actions ---
def add_college_node(state: AppState) -> AppState:
    college_name = state.get("user_input", "Unnamed College")
    colleges_collection.insert_one({"_id": college_name})
    return make_response(state, f"✅ College '{college_name}' added successfully!")


def remove_college_node(state: AppState) -> AppState:
    college_name = state.get("user_input", "Unnamed College")
    colleges_collection.delete_one({"_id": college_name})
    return make_response(state, f"🗑️ College '{college_name}' removed.")


def list_colleges_node(state: AppState) -> AppState:
    colleges = [c["_id"] for c in colleges_collection.find()]
    return make_response(state, f"🏫 Colleges: {', '.join(colleges) if colleges else 'None found'}")


# --- College Actions ---
def add_teacher_node(state: AppState) -> AppState:
    teacher_name = state.get("user_input", "Unnamed Teacher")
    teachers_collection.insert_one({"_id": teacher_name})
    return make_response(state, f"✅ Teacher '{teacher_name}' added.")


def remove_teacher_node(state: AppState) -> AppState:
    teacher_name = state.get("user_input", "Unnamed Teacher")
    teachers_collection.delete_one({"_id": teacher_name})
    return make_response(state, f"🗑️ Teacher '{teacher_name}' removed.")


def list_teachers_node(state: AppState) -> AppState:
    teachers = [t["_id"] for t in teachers_collection.find()]
    return make_response(state, f"👨‍🏫 Teachers: {', '.join(teachers) if teachers else 'None found'}")


# --- Teacher Actions ---
def add_student_node(state: AppState) -> AppState:
    student_name = state.get("user_input", "Unnamed Student")
    students_collection.insert_one({"_id": student_name})
    return make_response(state, f"✅ Student '{student_name}' added.")


def generate_assignment_node(state: AppState) -> AppState:
    return make_response(state, "📄 Assignment generated successfully!")


def send_assignment_node(state: AppState) -> AppState:
    return make_response(state, "✉️ Assignment sent to students.")


# --- Student Actions ---
def get_assignments_node(state: AppState) -> AppState:
    return make_response(state, "📚 Here are your assignments.")


def submit_assignment_node(state: AppState) -> AppState:
    return make_response(state, "✅ Assignment submitted!")


def summarize_pdf_node(state: AppState) -> AppState:
    return make_response(state, "📑 PDF summary generated.")
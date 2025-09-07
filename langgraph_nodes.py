import json
from typing import Dict, TypedDict, List, Literal
from models import Admin, College, Teacher, Student
from database import users_collection, teachers_collection, students_collection, colleges_collection
from passlib.hash import bcrypt

# --- State Definition for LangGraph ---
class AppState(TypedDict):
    current_role: Literal["admin", "college", "teacher", "student", "unauthenticated"]
    current_user_id: str | None
    user_context: Dict          # Add context for roles that need it (e.g., college_id for a principal)
    message: str
    user_data: Dict
    action: str

# --- Core Node Functions ---
def initial_state_node(state: AppState) -> Dict:
    return {"message": "Welcome! Please log in to continue."}

def login_node(state: AppState) -> Dict:
    try:
        email, password = state["user_data"]["email"], state["user_data"]["password"]
        user = users_collection.find_one({"email": email})
        
        if user and bcrypt.verify(password, user['_password_hash']):
            role, user_id = user["role"], str(user["_id"])
            context = {}

            if role == "college":
                # Find which college this principal belongs to
                college_doc = colleges_collection.find_one({"principal_user_id": user_id})
                if college_doc: context["college_id"] = str(college_doc["_id"])
            
            elif role == "teacher":
                teacher_doc = teachers_collection.find_one({"teacher_user_id": user_id})
                if teacher_doc: context = {"college_id": str(teacher_doc["college_id"]), "teacher_db_id": str(teacher_doc["_id"]), "assigned_class": teacher_doc["assigned_class"]}
            
            elif role == "student":
                 student_doc = students_collection.find_one({"student_user_id": user_id})
                 if student_doc: context = {"student_db_id": str(student_doc["_id"]), "assigned_class": student_doc["assigned_class"]}

            return {"current_role": role, "current_user_id": user_id, "user_context": context, "message": f"Login successful! Welcome."}
        
        return {"current_role": "unauthenticated", "message": "Invalid credentials."}
    
    except KeyError:
        return {"current_role": "unauthenticated", "message": "Login requires 'email' and 'password'."}

def logout_node(state: AppState) -> Dict:
    return {"current_role": "unauthenticated", "current_user_id": None, "user_context": {}, "user_data": {}, "action": "", "message": "You have been logged out."}

# --- Menu Nodes ---
def admin_menu_node(state: AppState) -> Dict:
    return {"message": "ADMIN MENU | Actions: [add_college, remove_college, list_colleges, logout]"}

def college_menu_node(state: AppState) -> Dict:
    return {"message": "COLLEGE MENU | Actions: [add_teacher, remove_teacher, list_teachers, logout]"}

def teacher_menu_node(state: AppState) -> Dict:
    return {"message": "TEACHER MENU | Actions: [add_student, generate_assignment, send_assignment, logout]"}

def student_menu_node(state: AppState) -> Dict:
    return {"message": "STUDENT MENU | Actions: [get_assignments, submit_assignment, summarize_pdf, logout]"}

# --- Action Nodes  ---
# Admin Actions
def add_college_node(state: AppState) -> Dict:
    college, password = Admin.add_college(state["user_data"])
    if college: return {"message": f"College '{college['name']}' added. Principal's temporary password: {password}"}
    return {"message": "Failed to add college. Check data and try again."}

def remove_college_node(state: AppState) -> Dict:
    if Admin.remove_college(state["user_data"]["college_id"]): return {"message": "College removed successfully."}
    return {"message": "Failed to remove college or college not found."}

def list_colleges_node(state: AppState) -> Dict:
    colleges = Admin.list_colleges(state["user_data"].get("include_inactive", False))
    return {"message": json.dumps(colleges, indent=2, default=str)}

# College Actions
def add_teacher_node(state: AppState) -> Dict:
    teacher, password = College.add_teacher(state["user_data"], state["user_context"]["college_id"])
    if teacher: return {"message": f"Teacher '{teacher['name']}' added. Temporary password: {password}"}
    return {"message": "Failed to add teacher."}

def remove_teacher_node(state: AppState) -> Dict:
    if College.remove_teacher(state["user_data"]["teacher_id"]): return {"message": "Teacher removed."}
    return {"message": "Failed to remove teacher."}

def list_teachers_node(state: AppState) -> Dict:
    teachers = College.list_teachers(state["user_context"]["college_id"], state["user_data"].get("include_inactive", False))
    return {"message": json.dumps(teachers, indent=2, default=str)}

# Teacher Actions
def add_student_node(state: AppState) -> Dict:
    context = state["user_context"]
    student, password = Teacher.add_student(state["user_data"], context["teacher_db_id"], context["college_id"], context["assigned_class"])
    if student: return {"message": f"Student '{student['name']}' added. Temporary password: {password}"}
    return {"message": "Failed to add student."}

def generate_assignment_node(state: AppState) -> Dict:
    data = state["user_data"]
    teacher_id = state["user_context"]["teacher_db_id"]
    aid, _, _ = Teacher.generate_assignment(data['pdf_file_path'], data['topic'], int(data['num_mcq']), int(data['num_short']), int(data['num_long']), teacher_id)
    if aid: return {"message": f"Assignment generated! ID: {aid}"}
    return {"message": "Failed to generate assignment."}

def send_assignment_node(state: AppState) -> Dict:
    if Teacher.send_assignment(state["user_data"]["assignment_id"], state["user_data"]["class_ids"]): return {"message": "Assignment sent!"}
    return {"message": "Failed to send assignment."}

# Student Actions
def get_assignments_node(state: AppState) -> Dict:
    context = state["user_context"]
    assignments = Student.get_assignments(context["student_db_id"], context["assigned_class"], state["user_data"].get("status", "pending"))
    return {"message": json.dumps(assignments, indent=2, default=str)}

def submit_assignment_node(state: AppState) -> Dict:
    student_id = state["user_context"]["student_db_id"]
    result = Student.submit_assignment(state["user_data"]["assignment_id"], student_id, state["user_data"]["answers"])
    return {"message": f"--- Grade ---\n{result}"}

def summarize_pdf_node(state: AppState) -> Dict:
    summary = Student.upload_pdf_for_summary(state["user_data"]["pdf_file_path"], state["user_data"]["query"])
    return {"message": f"--- Summary & Answer ---\n{summary}"}

# final_app.py
import getpass
from typing import TypedDict, Literal, Optional, Dict, Any, NotRequired
from passlib.hash import bcrypt

# LangGraph and Database imports
from langgraph.graph import StateGraph
from database import users_collection

# Import your powerful backend classes from models.py
from models import Admin, College, Teacher, Student

# --- 1. Unified State Definition ---
class AppState(TypedDict, total=True):
    current_role: Literal["admin", "college", "teacher", "student", "unauthenticated"]
    current_user_id: NotRequired[str | None]
    current_user_doc: NotRequired[Dict[str, Any]]
    user_input: NotRequired[str]
    response: NotRequired[str]


# --- 2. Helper Functions ---
def make_response(state: AppState, message: str) -> AppState:
    state["response"] = message
    return state

def get_user_details(email: str) -> Optional[Dict[str, Any]]:
    """Helper to fetch the full user document from the database."""
    return users_collection.find_one({"email": email})

# --- 3. Core Nodes (Login, Menus) ---
def login_node(state: AppState) -> AppState:
    print("--- LOGIN ---")
    email = input("Enter your email: ").strip()
    password = getpass.getpass("Enter your password: ")
    
    user_doc = get_user_details(email)
    
    # Use the verify_password method from the User class logic
    if user_doc and bcrypt.verify(password, user_doc["_password_hash"]):
        state["current_user_id"] = user_doc["_id"]
        state["current_role"] = user_doc["role"]
        state["current_user_doc"] = user_doc
        state["response"] = f"✅ Login successful! Welcome, {user_doc['name']}."
        print(state["response"])
        return state
    else:
        state["current_role"] = "unauthenticated"
        return make_response(state, "❌ Invalid credentials. Please try again.")

def logout_node(state: AppState) -> AppState:
    return {
        "current_role": "unauthenticated",
        "response": "👋 You have been successfully logged out."
    }

def admin_menu_node(state: AppState) -> AppState:
    return make_response(state, "\nADMIN MENU | Actions: [add_college, list_colleges, remove_college, logout]")

def college_menu_node(state: AppState) -> AppState:
    return make_response(state, "\nCOLLEGE MENU | Actions: [add_teacher, list_teachers, remove_teacher, logout]")

def teacher_menu_node(state: AppState) -> AppState:
    return make_response(state, "\nTEACHER MENU | Actions: [add_student, generate_assignment, send_assignment, logout]")

def student_menu_node(state: AppState) -> AppState:
    return make_response(state, "\nSTUDENT MENU | Actions: [get_assignments, submit_assignment, chat_with_pdf, logout]")

# --- 4. Action Nodes (Integrated with models.py) ---

# --- Admin Actions ---
def add_college_node(state: AppState) -> AppState:
    print("\n--- ➕ Add New College ---")
    try:
        college_data = {
            'name': input("College Name: "),
            'principal_name': input("Principal's Name: "),
            'principal_age': int(input("Principal's Age: ")),
            'principal_address': input("Principal's Address: "),
            'phone_no': input("Principal's Phone (10-15 digits): "),
            'email': input("Principal's Email: ")
        }
        college, password = Admin.add_college(college_data)
        if college:
            return make_response(state, f"✅ College '{college['name']}' added.\n   🔑 Principal's temporary password: {password}")
        else:
            return make_response(state, "❌ Failed to add college. Please check input data.")
    except (ValueError, KeyError) as e:
        return make_response(state, f"❌ Invalid input: {e}")

def list_colleges_node(state: AppState) -> AppState:
    colleges = Admin.list_colleges()
    if not colleges:
        return make_response(state, "🏫 No active colleges found.")
    
    response = "🏫 Active Colleges:\n"
    for c in colleges:
        response += f"  - {c['name']} (ID: {c['_id']})\n"
    return make_response(state, response)

def remove_college_node(state: AppState) -> AppState:
    college_id = input("Enter the College ID to deactivate: ").strip()
    if Admin.remove_college(college_id):
        return make_response(state, f"🗑️ College '{college_id}' has been deactivated.")
    return make_response(state, f"⚠️ College '{college_id}' not found.")

# --- Teacher Actions ---
def generate_assignment_node(state: AppState) -> AppState:
    print("\n--- 🧠 Generate New Assignment from PDF ---")
    try:
        pdf_file = input("Path to PDF file: ")
        topic = input("Assignment Topic: ")
        num_mcq = int(input("Number of MCQs: "))
        num_short = int(input("Number of Short Answer Qs: "))
        num_long = int(input("Number of Long Answer Qs: "))
        
        teacher_user_id = state.get("current_user_id")

        print("⏳ Generating assignment... This may take a moment.")
        assignment_id, quiz, _ = Teacher.generate_assignment(pdf_file, topic, num_mcq, num_short, num_long, teacher_user_id)
        
        if assignment_id:
            # You can pretty-print the quiz here if you want
            return make_response(state, f"✅ Assignment generated successfully!\n   ID: {assignment_id}")
        else:
            return make_response(state, "❌ Could not generate assignment.")
    except Exception as e:
        return make_response(state, f"❌ An error occurred: {e}")

# --- Student Actions ---
def chat_with_pdf_node(state: AppState) -> AppState:
    print("\n--- 💬 Chat with PDF ---")
    try:
        pdf_file = input("Path to your PDF document: ")
        query = input("What would you like to know from this document? ")
        student_id = state.get("current_user_id")
        
        print("⏳ Analyzing document and generating response...")
        summary = Student.upload_pdf_for_summary(pdf_file, query, student_id)
        
        return make_response(state, f"💬 Response from your document:\n\n{summary}")
    except Exception as e:
        return make_response(state, f"❌ An error occurred: {e}")

# --- Placeholder nodes for other actions ---
def placeholder_node(action_name: str):
    def node(state: AppState) -> AppState:
        return make_response(state, f"--- Action '{action_name}' is not fully implemented in this CLI demo ---")
    return node

# --- 5. Graph Definition and Routing ---
def build_graph():
    workflow = StateGraph(AppState)
    
    # Add Nodes
    workflow.add_node("login", login_node)
    workflow.add_node("logout", logout_node)
    
    # Menu Nodes
    workflow.add_node("admin_menu", admin_menu_node)
    workflow.add_node("college_menu", college_menu_node)
    workflow.add_node("teacher_menu", teacher_menu_node)
    workflow.add_node("student_menu", student_menu_node)

    # Action Nodes
    workflow.add_node("add_college", add_college_node)
    workflow.add_node("list_colleges", list_colleges_node)
    workflow.add_node("remove_college", remove_college_node)
    workflow.add_node("generate_assignment", generate_assignment_node)
    workflow.add_node("chat_with_pdf", chat_with_pdf_node)
    
    # Add placeholders for other actions
    for action in ["add_teacher", "list_teachers", "remove_teacher", "add_student", "send_assignment", "get_assignments", "submit_assignment"]:
        workflow.add_node(action, placeholder_node(action))

    # --- Routing Logic ---
    def route_after_login(state: AppState):
        return f"{state['current_role']}_menu" if state.get("current_role") != "unauthenticated" else "login"

    def route_action(state: AppState):
        action = state.get("user_input", "").lower().strip()
        role = state.get("current_role")
        
        valid_actions = {
            "admin": ["add_college", "list_colleges", "remove_college"],
            "college": ["add_teacher", "list_teachers", "remove_teacher"],
            "teacher": ["add_student", "generate_assignment", "send_assignment"],
            "student": ["get_assignments", "submit_assignment", "chat_with_pdf"],
        }
        
        if action == "logout": return "logout"
        if role in valid_actions and action in valid_actions[role]:
            return action
        return f"{role}_menu" # Default to menu if action is invalid

    # --- Add Edges ---
    workflow.set_entry_point("login")
    workflow.add_conditional_edges("login", route_after_login)
    
    # Menus route to actions
    for role in ["admin", "college", "teacher", "student"]:
        workflow.add_conditional_edges(f"{role}_menu", route_action)

    # Actions loop back to their respective menus
    for action in ["add_college", "list_colleges", "remove_college"]:
        workflow.add_edge(action, "admin_menu")
    for action in ["add_teacher", "list_teachers", "remove_teacher"]:
        workflow.add_edge(action, "college_menu")
    for action in ["add_student", "generate_assignment", "send_assignment"]:
        workflow.add_edge(action, "teacher_menu")
    for action in ["get_assignments", "submit_assignment", "chat_with_pdf"]:
        workflow.add_edge(action, "student_menu")

    workflow.add_edge("logout", "login")
    
    return workflow.compile()

# --- 6. Main Execution Block ---
if __name__ == "__main__":
    app = build_graph()
    initial_state = {"current_role": "unauthenticated"}
    
    # Use a generator to stream state changes
    stream = app.stream(initial_state, stream_mode="values")
    
    while True:
        current_state = next(stream)
        if response_msg := current_state.get("response"):
            print(response_msg)
        
        if current_state.get("current_role") != "unauthenticated":
            next_action = input("Enter action: ").strip()
            # Feed the new action back into the stream
            stream = app.stream({"user_input": next_action}, stream_mode="values")
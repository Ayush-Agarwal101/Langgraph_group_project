import streamlit as st
import uuid
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime, time, timezone

# LangGraph Imports
from langgraph.graph import StateGraph, END

# Your existing models and database connection
# NO CHANGES ARE NEEDED IN THESE OTHER FILES
from models import Admin, College, Teacher, Student, User
from database import users_collection

# --- 1. Define the LangGraph Application State ---
class AppState(TypedDict):
    user_instance: Optional[User]
    current_node: str
    response_message: Optional[str]
    error_message: Optional[str]
    data_payload: Any
    form_data: Optional[Dict[str, Any]]
    
# --- Role to Class Mapping ---
ROLE_CLASS_MAP = {
    "admin": Admin, "college": College,
    "teacher": Teacher, "student": Student
}

# --- 2. Define the Graph Nodes ---
# Each node performs a specific action and updates the state.

def login_node(state: AppState) -> AppState:
    """Processes login credentials."""
    email = state["form_data"].get("email")
    password = state["form_data"].get("password")
    user_doc = users_collection.find_one({"email": email, "active": True})
    
    if user_doc and User.verify_password(password, user_doc.get("_password_hash")):
        UserClass = ROLE_CLASS_MAP.get(user_doc["role"])
        user_instance = UserClass(**user_doc)
        return {**state, "user_instance": user_instance, "error_message": None}
    else:
        return {**state, "user_instance": None, "error_message": "Invalid credentials."}

def logout_node(state: AppState) -> AppState:
    """Clears the session to log out."""
    return AppState(user_instance=None, current_node="login_screen", response_message="Logged out.", data_payload=None, form_data=None)

def navigate_to_dashboard_node(state: AppState) -> AppState:
    """Sets the current node to the user's main menu screen."""
    role = state["user_instance"].role
    return {**state, "current_node": f"{role}_dashboard", "response_message": None, "data_payload": None}

def process_form_node(state: AppState) -> AppState:
    """A generic node to process form data by calling a method on the user instance."""
    form_data = state["form_data"]
    method_name = form_data.pop("method")
    user_instance = state["user_instance"]
    
    try:
        method_to_call = getattr(user_instance, method_name)
        result = method_to_call(**form_data)
        
        # Format a success message
        action_name = method_name.replace('_', ' ').capitalize()
        message = f"{action_name} successful!"
        if isinstance(result, tuple): # Methods like add_user return a password
            message += f" Temporary password: {result[1]}"

        return {**state, "response_message": message, "error_message": None}
    except Exception as e:
        return {**state, "error_message": str(e), "response_message": None}

def fetch_data_node(state: AppState) -> AppState:
    """A generic node to fetch data using a method on the user instance."""
    form_data = state["form_data"]
    method_name = form_data.pop("method")
    user_instance = state["user_instance"]
    
    try:
        method_to_call = getattr(user_instance, method_name)
        data = method_to_call(**form_data)
        return {**state, "data_payload": data, "error_message": None}
    except Exception as e:
        return {**state, "error_message": str(e), "data_payload": None}

# --- 3. Build the Graph ---
def create_graph() -> StateGraph:
    workflow = StateGraph(AppState)
    
    # Add Nodes
    workflow.add_node("login", login_node)
    workflow.add_node("logout", logout_node)
    workflow.add_node("navigate_to_dashboard", navigate_to_dashboard_node)
    workflow.add_node("process_form", process_form_node)
    workflow.add_node("fetch_data", fetch_data_node)

    # Define Routing
    def route_after_login(state: AppState):
        return "navigate_to_dashboard" if state["user_instance"] else "login"

    def route_after_action(state: AppState):
        # After any action, navigate back to the user's dashboard to refresh the view
        return "navigate_to_dashboard"

    workflow.set_entry_point("navigate_to_dashboard") # Start by trying to go to dashboard
    workflow.add_conditional_edges(
        "navigate_to_dashboard",
        lambda s: "login" if not s["user_instance"] else s["user_instance"].role,
        {"login": "login", "admin": END, "college": END, "teacher": END, "student": END}
    )
    workflow.add_conditional_edges("login", route_after_login)
    workflow.add_edge("process_form", "navigate_to_dashboard")
    workflow.add_edge("fetch_data", "navigate_to_dashboard")
    workflow.add_edge("logout", "login")

    return workflow.compile()

# --- 4. Streamlit UI Rendering ---
# These functions ONLY draw the UI. Logic is handled by the graph.
def render_login_screen(graph_runner):
    st.title("College Management System Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            graph_runner({"form_data": {"email": email, "password": password}}, "login")

def render_admin_dashboard(state: AppState, graph_runner):
    st.title("🛠️ Admin Dashboard")
    # ... UI for Admin ...
    st.write("Admin features are ready to be built here.")


def render_college_dashboard(state: AppState, graph_runner):
    st.title(f"🏫 Welcome, {state['user_instance'].name}")
    page = st.sidebar.radio("Menu", ["Teachers", "Students", "Classes", "Attendance"])
    
    if page == "Teachers":
        st.header("Manage Teachers")
        with st.form("add_teacher"):
            name = st.text_input("Teacher Name")
            email = st.text_input("Teacher Email")
            if st.form_submit_button("Add Teacher"):
                payload = {"form_data": {"method": "add_teacher", "data": {"name": name, "email": email}}}
                graph_runner(payload, "process_form")
        st.subheader("Current Teachers")
        teachers = state['user_instance'].list_users_by_role("teacher")
        for t in teachers:
            st.write(f"- {t['name']} ({t['email']})")

    # ... Add UI for other college features (Students, Classes, Attendance) ...

def render_teacher_dashboard(state: AppState, graph_runner):
    st.title(f"📚 Welcome, {state['user_instance'].name}")
    page = st.sidebar.radio("Menu", ["Study Materials", "Assignments", "Attendance"])

    if page == "Study Materials":
        st.header("Upload Study Material")
        with st.form("upload_material", clear_on_submit=True):
            subject = st.text_input("Subject")
            chapter = st.text_input("Chapter Name")
            uploaded_file = st.file_uploader("Upload PDF", type="pdf")
            if st.form_submit_button("Upload"):
                if uploaded_file and subject and chapter:
                    payload = {"form_data": {"method": "upload_study_material", "uploaded_file": uploaded_file, "subject": subject, "chapter": chapter}}
                    graph_runner(payload, "process_form")
        st.subheader("My Uploaded Materials")
        materials = state['user_instance'].get_study_materials()
        for m in materials:
            st.write(f"- **{m['subject']}**: {m['chapter']} ({m['original_filename']})")

    elif page == "Assignments":
        st.header("Manage Assignments")
        # UI for creating, editing, and publishing assignments
        # This would be a multi-step process managed by different nodes in a more complex graph

    # ... Add UI for Teacher Attendance ...

def render_student_dashboard(state: AppState, graph_runner):
    st.title(f"🎓 Welcome, {state['user_instance'].name}")
    page = st.sidebar.radio("Menu", ["Assignments", "My Grades", "Study Q&A"])

    if page == "Assignments":
        st.header("My Assignments")
        assignments = state['user_instance'].get_assignments()
        new, pending, missed, submitted = st.tabs(["New", "Pending", "Missed", "Submitted"])
        with pending:
            for a in assignments['pending']:
                st.subheader(a['title'])
                # Form for submission would go here
        with submitted:
            for a in assignments['submitted']:
                st.subheader(a['title'])
                st.write(f"**Score:** {a['submission']['score']}")
                st.write(f"**Feedback:** {a['submission']['feedback']}")
    
    elif page == "Study Q&A":
        st.header("Ask Questions")
        # This requires fetching materials first
        teacher_user = state['user_instance']
        # This part of the code needs adjustment, as the teacher's model is not directly accessible here.
        # For simplicity, we assume we have a way to list all materials.
        # A better approach would be to have a shared function or a specific node for this.
        # materials = teacher_user.get_study_materials() # This line needs a fix in a real scenario
        # if materials:
        #     material_options = {m['original_filename']: m['_id'] for m in materials}
        #     selected_material_name = st.selectbox("Select a document", list(material_options.keys()))
        #     query = st.text_area("Your question")
        #     if st.button("Ask"):
        #         material_id = material_options[selected_material_name]
        #         # Here you'd call a specific node to handle the query
        #         # For example: graph_runner({"form_data": {"method": "query_study_material", "material_id": material_id, "query": query}}, "fetch_data")
        # else:
        #     st.write("No study materials available.")

# --- 5. Main App Logic ---
def main():
    st.set_page_config(layout="wide")
    
    if "graph_app" not in st.session_state:
        st.session_state.graph_app = create_graph()
        st.session_state.graph_state = AppState(user_instance=None, current_node="login", data_payload=None, form_data=None)
        st.session_state.thread_id = str(uuid.uuid4())

    app = st.session_state.graph_app
    
    def graph_runner(payload: dict, entry_node: str):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        final_state = app.invoke(payload, config, debug=False)
        st.session_state.graph_state = final_state
        st.rerun()

    state = st.session_state.graph_state
    
    if state.get("response_message"):
        st.toast(state["response_message"], icon="✅")
    if state.get("error_message"):
        st.error(state["error_message"])

    # --- Main UI Router ---
    if not state.get("user_instance"):
        render_login_screen(graph_runner)
    else:
        role_dashboard_map = {
            "admin": render_admin_dashboard,
            "college": render_college_dashboard,
            "teacher": render_teacher_dashboard,
            "student": render_student_dashboard,
        }
        render_func = role_dashboard_map.get(state["user_instance"].role)
        if render_func:
            # Pass a fresh copy of state to avoid mutation issues
            render_func(dict(state), graph_runner)
        else:
            st.error(f"No dashboard available for role: {state['user_instance'].role}")
            if st.button("Logout"):
                graph_runner({}, "logout")

if __name__ == "__main__":
    main()
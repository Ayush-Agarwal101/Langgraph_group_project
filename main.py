import uuid
from typing import Any
from langgraph.graph import StateGraph, END
# ✅ FIX: Removed the redundant 'initial_state_node'
from langgraph_nodes import AppState, login_node, logout_node, \
    admin_menu_node, add_college_node, remove_college_node, list_colleges_node, \
    college_menu_node, add_teacher_node, remove_teacher_node, list_teachers_node, \
    teacher_menu_node, add_student_node, generate_assignment_node, send_assignment_node, \
    student_menu_node, get_assignments_node, submit_assignment_node, summarize_pdf_node

# --- Define the graph workflow ---
workflow = StateGraph(AppState)

# --- Add all nodes to the graph ---
workflow.add_node("login", login_node)
workflow.add_node("logout", logout_node)

# Role-specific menus
workflow.add_node("admin_menu", admin_menu_node)
workflow.add_node("college_menu", college_menu_node)
workflow.add_node("teacher_menu", teacher_menu_node)
workflow.add_node("student_menu", student_menu_node)

# Action nodes for each feature
workflow.add_node("add_college", add_college_node)
workflow.add_node("remove_college", remove_college_node)
workflow.add_node("list_colleges", list_colleges_node)
workflow.add_node("add_teacher", add_teacher_node)
workflow.add_node("remove_teacher", remove_teacher_node)
workflow.add_node("list_teachers", list_teachers_node)
workflow.add_node("add_student", add_student_node)
workflow.add_node("generate_assignment", generate_assignment_node)
workflow.add_node("send_assignment", send_assignment_node)
workflow.add_node("get_assignments", get_assignments_node)
workflow.add_node("submit_assignment", submit_assignment_node)
workflow.add_node("summarize_pdf", summarize_pdf_node)

# --- Define the graph's edges and routing logic ---
# ✅ FIX: Set 'login' as the true entry point and removed the old edge
workflow.set_entry_point("login")

def route_after_login(state: AppState): return state["current_role"]
workflow.add_conditional_edges("login", route_after_login, {
    "admin": "admin_menu", "college": "college_menu", "teacher": "teacher_menu",
    "student": "student_menu", "unauthenticated": "login"
})

def route_action(state: AppState):
    action = state.get("action", "").lower()
    # ✅ FIX: If no action is present, return a special signal to end the current stream.
    if not action:
        return "END_OF_TURN"
    return "logout" if action == "logout" else action

# Conditional routing from each menu to its actions
# ✅ FIX: Added the "END_OF_TURN" route to gracefully stop the stream after a menu.
workflow.add_conditional_edges("admin_menu", route_action, {"add_college": "add_college", "remove_college": "remove_college", "list_colleges": "list_colleges", "logout": "logout", "END_OF_TURN": END})
workflow.add_conditional_edges("college_menu", route_action, {"add_teacher": "add_teacher", "remove_teacher": "remove_teacher", "list_teachers": "list_teachers", "logout": "logout", "END_OF_TURN": END})
workflow.add_conditional_edges("teacher_menu", route_action, {"add_student": "add_student", "generate_assignment": "generate_assignment", "send_assignment": "send_assignment", "logout": "logout", "END_OF_TURN": END})
workflow.add_conditional_edges("student_menu", route_action, {"get_assignments": "get_assignments", "submit_assignment": "submit_assignment", "summarize_pdf": "summarize_pdf", "logout": "logout", "END_OF_TURN": END})

# After an action, loop back to the corresponding menu
workflow.add_edge("add_college", "admin_menu"); workflow.add_edge("remove_college", "admin_menu"); workflow.add_edge("list_colleges", "admin_menu")
workflow.add_edge("add_teacher", "college_menu"); workflow.add_edge("remove_teacher", "college_menu"); workflow.add_edge("list_teachers", "college_menu")
workflow.add_edge("add_student", "teacher_menu"); workflow.add_edge("generate_assignment", "teacher_menu"); workflow.add_edge("send_assignment", "teacher_menu")
workflow.add_edge("get_assignments", "student_menu"); workflow.add_edge("submit_assignment", "student_menu"); workflow.add_edge("summarize_pdf", "student_menu")

# The logout node is the only way to the end of the graph
workflow.add_edge("logout", END)

# --- Compile the graph ---
app = workflow.compile()
print("✅ LangGraph application compiled successfully with all features!")

# --- Example of how to run it (for testing) ---
# A real application (like a web server or CLI) would manage this interaction loop.
if __name__ == '__main__':
    
    print("\n--- Running a test interaction ---")
    
    # The 'config' dictionary persists the state across calls for a single "session".
    session_id = str(uuid.uuid4())
    config: dict[str, Any] = {
        "recursion_limit": 100,
        "configurable": {"thread_id": session_id}
    }
    
    # Each 'stream' call represents one step in the state machine.
    state = {}
    
    # ✅ FIX: Removed the initial call and start the test directly with the login attempt.
    # Step 1: Admin Login
    print("--- Attempting Admin Login ---")
    inputs = {
        "user_data": {
            "email": "admin@example.com", 
            "password": "abcd1234" 
        }
    }
    for event in app.stream(inputs, config=config):
        state = event
    
    response = state[next(iter(state))]
    print(f"MESSAGE: {response['message']}\n")

    if response.get("current_role") == "admin":
        print("--- Attempting to Add a College ---")
        action_inputs = {
            "action": "add_college",
            "user_data": {
                "name": "First Gen University",
                "principal_name": "Dr. Alan Turing",
                "principal_age": 41,
                "phone_no": "9876543210",
                "email": "principal.turing@fgu.edu"
            }
        }
        for event in app.stream(action_inputs, config=config):
            state = event
        
        response = state[next(iter(state))]
        print(f"MESSAGE: {response['message']}\n")

        # Step 4: Logout
        print("--- Attempting Logout ---")
        logout_input: dict[str, Any] = {"action": "logout", "user_data": {}}
        for event in app.stream(logout_input, config=config):
            state = event
        
        response = state[next(iter(state))]
        print(f"MESSAGE: {response['message']}\n")


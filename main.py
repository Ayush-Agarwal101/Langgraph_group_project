# main.py

import uuid
from langgraph.graph import StateGraph, END
from langgraph_nodes import (
    AppState,
    login_node, logout_node,
    admin_menu_node, add_college_node, remove_college_node, list_colleges_node,
    college_menu_node, add_teacher_node, remove_teacher_node, list_teachers_node,
    teacher_menu_node, add_student_node, generate_assignment_node, send_assignment_node,
    student_menu_node, get_assignments_node, submit_assignment_node, summarize_pdf_node
)
from langgraph.checkpoint.memory import MemorySaver

# --- Define the graph workflow ---
workflow = StateGraph(AppState)

# --- Add all nodes explicitly ---
workflow.add_node(login_node)
workflow.add_node(logout_node)

workflow.add_node(admin_menu_node)
workflow.add_node(college_menu_node)
workflow.add_node(teacher_menu_node)
workflow.add_node(student_menu_node)

workflow.add_node(add_college_node)
workflow.add_node(remove_college_node)
workflow.add_node(list_colleges_node)

workflow.add_node(add_teacher_node)
workflow.add_node(remove_teacher_node)
workflow.add_node(list_teachers_node)

workflow.add_node(add_student_node)
workflow.add_node(generate_assignment_node)
workflow.add_node(send_assignment_node)

workflow.add_node(get_assignments_node)
workflow.add_node(submit_assignment_node)
workflow.add_node(summarize_pdf_node)

# --- Entry point ---
workflow.set_entry_point("login")

# --- Routing after login ---
def route_after_login(state: AppState):
    return state.get("current_role", "unauthenticated")

workflow.add_conditional_edges("login", route_after_login, {
    "admin": "admin_menu",
    "college": "college_menu",
    "teacher": "teacher_menu",
    "student": "student_menu",
    "unauthenticated": "login"
})

# --- Route actions in menus ---
def route_action(state: AppState):
    action = (state.get("action") or "").lower()
    if not action:
        return END  # Properly end the turn
    state["action"] = ""  # Reset action after execution
    return "logout" if action == "logout" else action

# --- Admin menu edges ---
workflow.add_conditional_edges("admin_menu", route_action, {
    "add_college": "add_college",
    "remove_college": "remove_college",
    "list_colleges": "list_colleges",
    "logout": "logout"
})

# --- College menu edges ---
workflow.add_conditional_edges("college_menu", route_action, {
    "add_teacher": "add_teacher",
    "remove_teacher": "remove_teacher",
    "list_teachers": "list_teachers",
    "logout": "logout"
})

# --- Teacher menu edges ---
workflow.add_conditional_edges("teacher_menu", route_action, {
    "add_student": "add_student",
    "generate_assignment": "generate_assignment",
    "send_assignment": "send_assignment",
    "logout": "logout"
})

# --- Student menu edges ---
workflow.add_conditional_edges("student_menu", route_action, {
    "get_assignments": "get_assignments",
    "submit_assignment": "submit_assignment",
    "summarize_pdf": "summarize_pdf",
    "logout": "logout"
})

# --- Loop back after action to corresponding menu ---
workflow.add_edge("add_college", "admin_menu")
workflow.add_edge("remove_college", "admin_menu")
workflow.add_edge("list_colleges", "admin_menu")

workflow.add_edge("add_teacher", "college_menu")
workflow.add_edge("remove_teacher", "college_menu")
workflow.add_edge("list_teachers", "college_menu")

workflow.add_edge("add_student", "teacher_menu")
workflow.add_edge("generate_assignment", "teacher_menu")
workflow.add_edge("send_assignment", "teacher_menu")

workflow.add_edge("get_assignments", "student_menu")
workflow.add_edge("submit_assignment", "student_menu")
workflow.add_edge("summarize_pdf", "student_menu")

# Logout leads to END
workflow.add_edge("logout", END)

# --- Compile the graph ---
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

print("✅ LangGraph application compiled successfully!")

# --- Optional: global recursion limit ---
config = {"configurable": {"recursion_limit": 30}}

# app.py
import streamlit as st
import getpass
from typing import Dict, Any
from database import users_collection
from models import Admin, College, Teacher, Student

# --- Helpers ---
def get_user_details(email: str) -> Dict[str, Any] | None:
    return users_collection.find_one({"email": email})

def login(email: str, password: str):
    user_doc = get_user_details(email)
    if user_doc and Student.verify_password(password, user_doc.get("_password_hash")):
        st.session_state["current_role"] = user_doc["role"]
        st.session_state["current_user_id"] = user_doc["_id"]
        st.session_state["current_user_doc"] = user_doc
        return True, f"✅ Login successful! Welcome, {user_doc['name']}."
    return False, "❌ Invalid credentials. Please try again."

def logout():
    st.session_state.clear()
    st.success("👋 Logged out successfully.")

# --- UI Pages ---
def login_page():
    st.title("🔐 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, msg = login(email, password)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

def admin_menu():
    st.title("🛠️ Admin Dashboard")
    st.subheader("Actions")
    if st.button("➕ Add College"):
        with st.form("add_college_form"):
            name = st.text_input("College Name")
            principal_name = st.text_input("Principal Name")
            principal_age = st.number_input("Principal Age", min_value=20, max_value=100, step=1)
            principal_address = st.text_area("Principal Address")
            phone_no = st.text_input("Phone No")
            email = st.text_input("Principal Email")
            submit = st.form_submit_button("Submit")
            if submit:
                try:
                    college, password = Admin.add_college({
                        "name": name,
                        "principal_name": principal_name,
                        "principal_age": principal_age,
                        "principal_address": principal_address,
                        "phone_no": phone_no,
                        "email": email
                    })
                    st.success(f"✅ College '{college['name']}' added. Temporary password: {password}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    if st.button("📋 List Colleges"):
        colleges = Admin.list_colleges()
        if colleges:
            for c in colleges:
                st.write(f"- {c['name']} (ID: {c['_id']})")
        else:
            st.warning("🏫 No colleges found.")

    with st.form("remove_college_form"):
        college_id = st.text_input("Enter College ID to deactivate")
        submit = st.form_submit_button("Remove")
        if submit:
            if Admin.remove_college(college_id):
                st.success(f"🗑️ College '{college_id}' removed.")
            else:
                st.error("⚠️ College not found.")

    if st.button("Logout"):
        logout()
        st.rerun()

def teacher_menu():
    st.title("📚 Teacher Dashboard")
    if st.button("🧠 Generate Assignment"):
        with st.form("assignment_form"):
            pdf_file = st.text_input("PDF File Path")
            topic = st.text_input("Topic")
            num_mcq = st.number_input("MCQs", 0, 20, 5)
            num_short = st.number_input("Short Qs", 0, 10, 2)
            num_long = st.number_input("Long Qs", 0, 10, 2)
            submit = st.form_submit_button("Generate")
            if submit:
                try:
                    assignment_id, quiz, _ = Teacher.generate_assignment(
                        pdf_file, topic, num_mcq, num_short, num_long, st.session_state["current_user_id"]
                    )
                    st.success(f"✅ Assignment created: {assignment_id}")
                except Exception as e:
                    st.error(f"❌ {e}")
    if st.button("Logout"):
        logout()
        st.rerun()

def student_menu():
    st.title("🎓 Student Dashboard")
    if st.button("💬 Chat with PDF"):
        with st.form("chat_form"):
            pdf_file = st.text_input("PDF File Path")
            query = st.text_area("Ask a question")
            submit = st.form_submit_button("Ask")
            if submit:
                try:
                    answer = Student.upload_pdf_for_summary(pdf_file, query, st.session_state["current_user_id"])
                    st.info(answer)
                except Exception as e:
                    st.error(f"❌ {e}")
    if st.button("Logout"):
        logout()
        st.rerun()

# --- Main ---
def main():
    if "current_role" not in st.session_state:
        login_page()
    else:
        role = st.session_state["current_role"]
        if role == "admin":
            admin_menu()
        elif role == "teacher":
            teacher_menu()
        elif role == "student":
            student_menu()
        elif role == "college":
            st.warning("🏫 College menu not fully implemented.")
            if st.button("Logout"):
                logout()
                st.rerun()

if __name__ == "__main__":
    main()

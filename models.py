# models.py
import uuid
from typing import Dict, Any, List, Tuple, Optional
from passlib.hash import bcrypt

from database import (
    users_collection,
    colleges_collection,
    teachers_collection,
    students_collection,
    assignments_collection,
    submissions_collection,
)


# -----------------------------
# Base User class
# -----------------------------
class User:
    def __init__(self, _id: str, name: str, email: str, _password_hash: str, role: str):
        self._id = _id
        self.name = name
        self.email = email
        self._password_hash = _password_hash
        self.role = role

    # --- Password helpers ---
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.verify(password, password_hash)


# -----------------------------
# Admin class
# -----------------------------
class Admin(User):

    @staticmethod
    def add_college(college_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create a college + principal login."""
        existing = colleges_collection.find_one({"email": college_data["email"]})
        if existing:
            return None, None

        principal_password = str(uuid.uuid4())[:8]
        password_hash = User.hash_password(principal_password)

        college_doc = {
            "_id": str(uuid.uuid4()),
            "name": college_data["name"],
            "principal_name": college_data["principal_name"],
            "principal_age": college_data["principal_age"],
            "principal_address": college_data["principal_address"],
            "phone_no": college_data["phone_no"],
            "email": college_data["email"],
            "_password_hash": password_hash,
            "role": "college",
            "active": True,
        }

        colleges_collection.insert_one(college_doc)
        users_collection.insert_one(college_doc)  # add to users too

        return college_doc, principal_password

    @staticmethod
    def list_colleges() -> List[Dict[str, Any]]:
        return list(colleges_collection.find({"active": True}))

    @staticmethod
    def remove_college(college_id: str) -> bool:
        result = colleges_collection.update_one(
            {"_id": college_id}, {"$set": {"active": False}}
        )
        return result.modified_count > 0


# -----------------------------
# College class
# -----------------------------
class College(User):

    @staticmethod
    def add_teacher(college_id: str, teacher_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        existing = teachers_collection.find_one({"email": teacher_data["email"]})
        if existing:
            return None, None

        teacher_password = str(uuid.uuid4())[:8]
        password_hash = User.hash_password(teacher_password)

        teacher_doc = {
            "_id": str(uuid.uuid4()),
            "college_id": college_id,
            "name": teacher_data["name"],
            "email": teacher_data["email"],
            "_password_hash": password_hash,
            "role": "teacher",
            "active": True,
        }

        teachers_collection.insert_one(teacher_doc)
        users_collection.insert_one(teacher_doc)

        return teacher_doc, teacher_password

    @staticmethod
    def list_teachers(college_id: str) -> List[Dict[str, Any]]:
        return list(teachers_collection.find({"college_id": college_id, "active": True}))

    @staticmethod
    def remove_teacher(teacher_id: str) -> bool:
        result = teachers_collection.update_one(
            {"_id": teacher_id}, {"$set": {"active": False}}
        )
        return result.modified_count > 0


# -----------------------------
# Teacher class
# -----------------------------
class Teacher(User):

    @staticmethod
    def add_student(teacher_id: str, student_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        existing = students_collection.find_one({"email": student_data["email"]})
        if existing:
            return None, None

        student_password = str(uuid.uuid4())[:8]
        password_hash = User.hash_password(student_password)

        student_doc = {
            "_id": str(uuid.uuid4()),
            "teacher_id": teacher_id,
            "name": student_data["name"],
            "email": student_data["email"],
            "_password_hash": password_hash,
            "role": "student",
            "active": True,
        }

        students_collection.insert_one(student_doc)
        users_collection.insert_one(student_doc)

        return student_doc, student_password

    @staticmethod
    def generate_assignment(
        pdf_file: str,
        topic: str,
        num_mcq: int,
        num_short: int,
        num_long: int,
        teacher_id: str,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Placeholder for assignment generation.
        TODO: Integrate LangChain or custom logic for real quiz generation.
        """
        assignment_id = str(uuid.uuid4())
        assignment_doc = {
            "_id": assignment_id,
            "teacher_id": teacher_id,
            "topic": topic,
            "pdf_file": pdf_file,
            "quiz": {
                "mcq": [],
                "short": [],
                "long": []
            },
        }
        assignments_collection.insert_one(assignment_doc)
        return assignment_id, assignment_doc, None


# -----------------------------
# Student class
# -----------------------------
class Student(User):

    @staticmethod
    def upload_pdf_for_summary(pdf_file: str, query: str, student_id: str) -> str:
        """
        Placeholder for LangChain PDF QA logic.
        TODO: Replace with actual vector store + retrieval QA.
        """
        return f"Summary/Answer for query '{query}' from PDF '{pdf_file}'."

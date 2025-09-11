import uuid
import os
import re
from typing import Dict, Any, List, Tuple
from passlib.hash import bcrypt
from datetime import datetime, timezone
import ai_services 
import tempfile

# New imports for the RAG preprocessing pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from database import (
    users_collection, colleges_collection, classes_collection,
    enrollments_collection, study_materials_collection, assignments_collection,
    submissions_collection, attendance_collection, fs,
    study_material_chunks_collection # Import new collection
)

# --- Base User Class ---
class User:
    def __init__(self, _id: str, name: str, email: str, role: str, **kwargs):
        self._id = _id
        self.name = name
        self.email = email
        self.role = role
        self._raw_doc = kwargs
        self._raw_doc.update({"_id": _id, "name": name, "email": email, "role": role})

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.verify(password, password_hash) if password and password_hash else False

# --- Admin Class ---
class Admin(User):
    def add_college(self, data: Dict[str, Any]) -> Tuple[Dict, str]:
        if users_collection.find_one({"email": data["email"]}):
            raise ValueError(f"User with email {data['email']} already exists.")
        
        password = str(uuid.uuid4())[:8]
        principal_user = {
            "_id": str(uuid.uuid4()), "name": data["principal_name"], "email": data["email"],
            "_password_hash": self.hash_password(password), "role": "college", "active": True
        }
        users_collection.insert_one(principal_user)
        
        college = {
            "_id": str(uuid.uuid4()), "name": data["name"], "address": data["address"],
            "principal_user_id": principal_user["_id"], "active": True
        }
        colleges_collection.insert_one(college)
        return college, password

    def list_colleges(self, active=True) -> List[Dict]:
        return list(colleges_collection.find({"active": active}))

    def toggle_college_status(self, college_id: str) -> bool:
        college = colleges_collection.find_one({"_id": college_id})
        if not college: return False
        new_status = not college.get("active", True)
        result = colleges_collection.update_one({"_id": college_id}, {"$set": {"active": new_status}})
        users_collection.update_one({"_id": college["principal_user_id"]}, {"$set": {"active": new_status}})
        return result.modified_count > 0

# --- College (Principal) Class ---
class College(User):
    def get_my_college_info(self) -> Dict:
        return colleges_collection.find_one({"principal_user_id": self._id})

    def _create_user(self, data: Dict[str, Any], role: str) -> Tuple[Dict, str]:
        if users_collection.find_one({"email": data["email"]}):
            raise ValueError(f"User with email {data['email']} already exists.")
        
        password = str(uuid.uuid4())[:8]
        user_doc = {
            "_id": str(uuid.uuid4()), "name": data["name"], "email": data["email"],
            "_password_hash": self.hash_password(password), "role": role,
            "college_id": self.get_my_college_info()["_id"], "active": True
        }
        users_collection.insert_one(user_doc)
        return user_doc, password

    def add_teacher(self, data: Dict[str, Any]) -> Tuple[Dict, str]:
        return self._create_user(data, "teacher")

    def add_student(self, data: Dict[str, Any]) -> Tuple[Dict, str]:
        return self._create_user(data, "student")
    
    def list_users_by_role(self, role: str, active=True) -> List[Dict]:
        college_id = self.get_my_college_info()["_id"]
        return list(users_collection.find({"role": role, "college_id": college_id, "active": active}))

    def mark_teacher_attendance(self, teacher_id: str, status: str):
        today = datetime.now().strftime("%Y-%m-%d")
        attendance_collection.update_one(
            {"user_id": teacher_id, "date": today},
            {"$set": {"status": status, "marked_by_id": self._id, "role": "teacher"}},
            upsert=True
        )
        
# --- Teacher Class ---
class Teacher(User):
    def get_my_college_id(self) -> str:
        return self._raw_doc.get("college_id")

    def get_my_classes(self) -> List[Dict]:
        return list(classes_collection.find({"teacher_id": self._id, "college_id": self.get_my_college_id()}))

    def mark_student_attendance(self, student_id: str, class_id: str, status: str):
        today = datetime.now().strftime("%Y-%m-%d")
        attendance_collection.update_one(
            {"user_id": student_id, "class_id": class_id, "date": today},
            {"$set": {"status": status, "marked_by_id": self._id, "role": "student"}},
            upsert=True
        )

    def upload_study_material(self, uploaded_file, subject: str, chapter: str) -> Dict:
        """
        Uploads a file, processes it into chunks, creates embeddings,
        and stores everything in MongoDB and GridFS.
        """
        # 1. Save the original file to GridFS
        file_id = fs.upload_from_stream(uploaded_file.name, uploaded_file)
        
        # 2. Save the metadata to our main materials collection
        material_doc = {
            "_id": str(uuid.uuid4()), "teacher_id": self._id, "subject": subject,
            "chapter": chapter, "gridfs_file_id": file_id,
            "original_filename": uploaded_file.name, "uploaded_at": datetime.now(timezone.utc)
        }
        study_materials_collection.insert_one(material_doc)
        
        # 3. Process the PDF for RAG (Load -> Split -> Embed -> Store)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            uploaded_file.seek(0)
            tmp_file.write(uploaded_file.read())
            temp_path = tmp_file.name

        try:
            loader = PyPDFLoader(temp_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            
            # Add our material_id to the metadata of each chunk for filtering later
            for split in splits:
                split.metadata['material_id'] = material_doc['_id']

            # 4. Store the chunks and their embeddings in our vector store
            ai_services.vector_search.add_documents(splits)

        finally:
            os.remove(temp_path)

        return material_doc

    def get_study_materials(self) -> List[Dict]:
        return list(study_materials_collection.find({"teacher_id": self._id}))

    def create_assignment_draft(self, class_id: str, title: str, source_material_id: str, topic: str, num_mcq: int, num_short: int, num_long: int) -> Dict:
        material_doc = study_materials_collection.find_one({"_id": source_material_id})
        if not material_doc:
            raise ValueError("Source material not found.")
        
        gridfs_file = fs.get(material_doc['gridfs_file_id'])
        content = gridfs_file.read().decode('utf-8', errors='ignore')
        
        structured_quiz = ai_services.generate_structured_quiz_from_text(content, topic, num_mcq, num_short, num_long)
        
        questions, answers = [], []
        
        for mcq in structured_quiz.mcqs:
            q_id = str(uuid.uuid4())
            questions.append({"q_id": q_id, "type": "MCQ", "text": mcq.question_text, "options": mcq.options})
            answers.append({"q_id": q_id, "answer": mcq.options[mcq.correct_answer_index]})
        for short_q in structured_quiz.short_answers:
            q_id = str(uuid.uuid4())
            questions.append({"q_id": q_id, "type": "SHORT", "text": short_q.question_text})
            answers.append({"q_id": q_id, "answer": short_q.ideal_answer})
        for long_q in structured_quiz.long_answers:
            q_id = str(uuid.uuid4())
            questions.append({"q_id": q_id, "type": "LONG", "text": long_q.question_text})
            answers.append({"q_id": q_id, "answer": long_q.ideal_answer})

        assignment_doc = {
            "_id": str(uuid.uuid4()), "teacher_id": self._id, "class_id": class_id,
            "title": title, "status": "draft", "questions": questions, "answers": answers,
            "created_at": datetime.now(timezone.utc)
        }
        assignments_collection.insert_one(assignment_doc)
        return assignment_doc
        
    def update_assignment_draft(self, assignment_id: str, questions: List[Dict]):
        assignments_collection.update_one({"_id": assignment_id}, {"$set": {"questions": questions}})

    def publish_assignment(self, assignment_id: str, start_time: datetime, due_time: datetime):
        assignments_collection.update_one(
            {"_id": assignment_id, "teacher_id": self._id},
            {"$set": {"status": "published", "start_time": start_time, "due_time": due_time}}
        )

# --- Student Class ---
class Student(User):
    def get_my_enrollments(self) -> List[Dict]:
        return list(enrollments_collection.find({"student_id": self._id, "status": "current"}))

    def get_assignments(self) -> Dict[str, List]:
        enrollments = self.get_my_enrollments()
        class_ids = [e['class_id'] for e in enrollments]
        now = datetime.now(timezone.utc)
        
        assignments = list(assignments_collection.find({
            "class_id": {"$in": class_ids},
            "status": "published"
        }))
        my_submissions = list(submissions_collection.find({"student_id": self._id}))
        submitted_ids = {s['assignment_id'] for s in my_submissions}

        categorized = {"new": [], "pending": [], "missed": [], "submitted": []}

        for assign in assignments:
            assign_id = assign["_id"]
            due_time = assign.get("due_time")
            start_time = assign.get("start_time")

            if assign_id in submitted_ids:
                submission = next((s for s in my_submissions if s['assignment_id'] == assign_id), None)
                assign['submission'] = submission
                categorized["submitted"].append(assign)
            elif due_time and now > due_time:
                categorized["missed"].append(assign)
            elif start_time and now >= start_time:
                categorized["pending"].append(assign)
            else:
                categorized["new"].append(assign)
                
        return categorized

    def submit_assignment(self, assignment_id: str, student_answers: List[Dict]):
        submission_id = str(uuid.uuid4())
        submission_doc = {
            "_id": submission_id, "assignment_id": assignment_id, "student_id": self._id,
            "answers": student_answers, "submitted_at": datetime.now(timezone.utc),
            "graded": False, "score": None, "feedback": None
        }
        submissions_collection.insert_one(submission_doc)

        assignment = assignments_collection.find_one({"_id": assignment_id})
        questions_with_answers = []
        for q in assignment['questions']:
            correct_ans = next((a['answer'] for a in assignment['answers'] if a['q_id'] == q['q_id']), "N/A")
            questions_with_answers.append({"q_id": q['q_id'], "type": q['type'], "text": q['text'], "answer": correct_ans})
            
        grading_result = ai_services.grade_submission(questions_with_answers, student_answers)
        
        score_match = re.search(r"Total Score: (.*?)\n", grading_result)
        feedback_match = re.search(r"Overall Feedback: (.*)", grading_result, re.DOTALL)
        score = score_match.group(1).strip() if score_match else "Grading Error"
        feedback = feedback_match.group(1).strip() if feedback_match else "Could not generate feedback."
        
        submissions_collection.update_one(
            {"_id": submission_id},
            {"$set": {"graded": True, "score": score, "feedback": feedback}}
        )

    def query_study_material(self, material_id: str, query: str) -> str:
        """Queries pre-processed study material using the efficient RAG pipeline."""
        return ai_services.answer_query_with_rag(query, material_id)
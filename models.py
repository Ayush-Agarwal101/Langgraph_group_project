import uuid
import re
import json
import os
from passlib.hash import bcrypt
from datetime import datetime
from database import *
from huggingface_hub import InferenceClient, login
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# --- Hugging Face Setup ---
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
if HUGGING_FACE_TOKEN:
    login(token=HUGGING_FACE_TOKEN)
else:
    print("⚠️ Hugging Face token not found. Set HUGGING_FACE_TOKEN in your .env file for full functionality.")

MODEL_NAME = os.environ.get("HF_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
EMBEDDINGS_MODEL = os.environ.get("HF_EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")

llm = InferenceClient(model=MODEL_NAME)
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)


# --- Pydantic Models for Structured LLM Output ---
class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class ShortAnswer(BaseModel):
    question: str
    answer: str

class LongAnswer(BaseModel):
    question: str
    answer: str

class QuizAndAnswerKey(BaseModel):
    mcqs: List[MCQ] = Field(description="A list of multiple-choice questions.")
    short_answers: List[ShortAnswer] = Field(description="A list of short answer questions.")
    long_answers: List[LongAnswer] = Field(description="A list of long answer questions.")


# --- Mixins and Base Class ---
class PasswordMixin:
    _password_hash: Optional[str] = None
    @property
    def password(self): return "****"
    @password.setter
    def password(self, plain_text): self._password_hash = bcrypt.hash(plain_text)
    def verify_password(self, plain_text):
        if self._password_hash is None:
            return False
        return bcrypt.verify(plain_text, self._password_hash)

class User(PasswordMixin):
    def __init__(self, _id, name, age, address, phone_no, email, password, role):
        if not self._is_valid_phone(phone_no): raise ValueError("Invalid phone number format.")
        if not self._is_valid_email(email): raise ValueError("Invalid email address format.")
        if not self._is_valid_age(age): raise ValueError("Please enter a correct age.")
        self._id, self.name, self.age, self.address, self.phone_no, self.email, self.role = _id, name, age, address, phone_no, email, role
        self.password = password

    def _is_valid_phone(self, phone_no): return bool(re.match(r'^\d{10,15}$', str(phone_no)))
    def _is_valid_email(self, email): return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
    def _is_valid_age(self, age):
        try: return 0 < int(age) < 120
        except (ValueError, TypeError): return False

# --- Admin Class ---
class Admin(User):
    def __init__(self, _id, name, age, address, phone_no, email, password):
        super().__init__(_id, name, age, address, phone_no, email, password, role="admin")
    
    @staticmethod
    def add_college(college_data):
        try:
            principal_password = str(uuid.uuid4())[:8]
            principal_user = User(_id=str(uuid.uuid4()), name=college_data['principal_name'], age=college_data.get('principal_age'), address=college_data.get('principal_address'), phone_no=college_data['phone_no'], email=college_data['email'], password=principal_password, role="college")
            
            user_doc = {"_id": principal_user._id, "name": principal_user.name, "email": principal_user.email, "_password_hash": principal_user._password_hash, "role": "college"}
            users_collection.insert_one(user_doc)

            college_doc = {"_id": str(uuid.uuid4()), "name": college_data['name'], "principal_name": college_data['principal_name'], "email": college_data['email'], "principal_user_id": principal_user._id, "active": True}
            colleges_collection.insert_one(college_doc)
            return college_doc, principal_password
        except (ValueError, KeyError) as e:
            print(f"Error adding college: {e}")
            return None, None
            
    @staticmethod
    def remove_college(college_id):
        result = colleges_collection.update_one({"_id": college_id}, {"$set": {"active": False}})
        return result.modified_count > 0
        
    @staticmethod
    def list_colleges(include_inactive=False):
        query = {} if include_inactive else {"active": True}
        return list(colleges_collection.find(query))

# --- College Class ---
class College(PasswordMixin):
    @staticmethod
    def add_teacher(teacher_data, college_id):
        try:
            teacher_password = str(uuid.uuid4())[:8]
            teacher_user = User(_id=str(uuid.uuid4()), name=teacher_data['name'], age=teacher_data['age'], address=teacher_data['address'], phone_no=teacher_data['phone_no'], email=teacher_data['email'], password=teacher_password, role="teacher")
            
            user_doc = {"_id": teacher_user._id, "name": teacher_user.name, "email": teacher_user.email, "_password_hash": teacher_user._password_hash, "role": "teacher"}
            users_collection.insert_one(user_doc)

            teacher_doc = {"_id": str(uuid.uuid4()), "name": teacher_data['name'], "email": teacher_data['email'], "assigned_class": teacher_data['assigned_class'], "college_id": college_id, "teacher_user_id": teacher_user._id, "active": True}
            teachers_collection.insert_one(teacher_doc)
            return teacher_doc, teacher_password
        except (ValueError, KeyError) as e:
            print(f"Error adding teacher: {e}")
            return None, None

    @staticmethod
    def remove_teacher(teacher_id):
        result = teachers_collection.update_one({"_id": teacher_id}, {"$set": {"active": False}})
        return result.modified_count > 0

    @staticmethod
    def list_teachers(college_id, include_inactive=False):
        query = {"college_id": college_id}
        if not include_inactive: query["active"] = True
        return list(teachers_collection.find(query))

# --- Teacher Class ---
class Teacher(User):
    @staticmethod
    def add_student(student_data, teacher_id, college_id, assigned_class):
        try:
            student_password = str(uuid.uuid4())[:8]
            student_user = User(_id=str(uuid.uuid4()), name=student_data['name'], age=student_data['age'], address=student_data['address'], phone_no=student_data['phone_no'], email=student_data['email'], password=student_password, role="student")
            
            user_doc = {"_id": student_user._id, "name": student_user.name, "email": student_user.email, "_password_hash": student_user._password_hash, "role": "student"}
            users_collection.insert_one(user_doc)

            student_doc = {"_id": str(uuid.uuid4()), "name": student_data['name'], "email": student_data['email'], "assigned_class": assigned_class, "college_id": college_id, "teacher_id": teacher_id, "student_user_id": student_user._id, "active": True}
            students_collection.insert_one(student_doc)
            return student_doc, student_password
        except (ValueError, KeyError) as e:
            print(f"Error adding student: {e}")
            return None, None

    @staticmethod
    def generate_assignment(pdf_file, topic, num_mcq, num_short, num_long, teacher_id):
        try:
            loader = PyPDFLoader(pdf_file)
            documents = loader.load_and_split(text_splitter=RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200))
            vectorstore = FAISS.from_documents(documents, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={'k': 5})
            
            schema_json = json.dumps(QuizAndAnswerKey.model_json_schema(), indent=2)
            prompt_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert quiz generator. Your task is to create a quiz based on the provided context and topic. You must adhere strictly to the requested number of questions for each type. Your entire output must be a single, valid JSON object that conforms to the provided JSON schema. Do not include any text before or after the JSON object.<|eot_id|><|start_header_id|>user<|end_header_id|>
Context: {context}

Topic: '{topic}'

Please generate a quiz with:
- {num_mcq} multiple-choice questions.
- {num_short} short answer questions.
- {num_long} long answer questions.

Your response must be a JSON object matching this schema:
{schema}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
            
            quiz_prompt = PromptTemplate.from_template(prompt_template)
            context_text = "\n\n".join([doc.page_content for doc in retriever.get_relevant_documents(topic)])
            formatted_prompt = quiz_prompt.format(context=context_text, topic=topic, num_mcq=num_mcq, num_short=num_short, num_long=num_long, schema=schema_json)
            response_text = llm.text_generation(prompt=formatted_prompt, max_new_tokens=4096)
            
            json_str = response_text.strip()
            if '```json' in json_str:
                match = re.search(r'```json\s*([\s\S]*?)\s*```', json_str)
                if match:
                    json_str = match.group(1)

            parsed_quiz_data = QuizAndAnswerKey.model_validate_json(json_str)
            
            quiz_content = parsed_quiz_data.model_dump()
            
            answer_key_dict = {
                "mcqs_answers": [{"q": q.question, "a": q.correct_answer} for q in parsed_quiz_data.mcqs],
                "short_answers": [{"q": q.question, "a": q.answer} for q in parsed_quiz_data.short_answers],
                "long_answers": [{"q": q.question, "a": q.answer} for q in parsed_quiz_data.long_answers],
            }
            
            assignment_id = str(uuid.uuid4())
            assignments_collection.insert_one({
                "_id": assignment_id,
                "teacher_id": teacher_id,
                "topic": topic,
                "quiz_content": quiz_content,
                "answer_key": answer_key_dict,
                "created_at": datetime.now(),
                "is_sent": False,
                "sent_to_classes": []
            })
            return assignment_id, quiz_content, answer_key_dict
        
        except Exception as e:
            print(f"❌ Failed to generate or parse assignment: {e}")
            return None, None, None

    @staticmethod
    def send_assignment(assignment_id, class_ids):
        result = assignments_collection.update_one(
            {"_id": assignment_id},
            {"$set": {"sent_to_classes": class_ids, "is_sent": True}}
        )
        return result.modified_count > 0

# --- Student Class ---
class Student(User):
    @staticmethod
    def get_assignments(student_id, assigned_class, status="pending"):
        # Find all assignments this student has already submitted
        submitted_ids = [sub['assignment_id'] for sub in submissions_collection.find(
            {"student_id": student_id},
            {"assignment_id": 1}
        )]
        
        if status == "pending":
            # Find assignments sent to the student's class that are NOT in their submitted list
            query = {"sent_to_classes": assigned_class, "_id": {"$nin": submitted_ids}}
        elif status == "submitted":
            # Find assignments that ARE in their submitted list
            query = {"_id": {"$in": submitted_ids}}
        else: # "all"
            query = {"sent_to_classes": assigned_class}
        
        return list(assignments_collection.find(query))

    @staticmethod
    def submit_assignment(assignment_id, student_id, answers):
        assignment = assignments_collection.find_one({"_id": assignment_id})
        if not assignment:
            return "Assignment not found."
            
        answer_key = json.dumps(assignment['answer_key'], indent=2)
        student_answers_str = json.dumps(answers, indent=2)
        
        grade_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an intelligent grading assistant. Your task is to evaluate a student's submission against the official answer key.
Provide a numerical score out of 100 and concise feedback for each question.
Be fair and consider partial credit for answers that are conceptually correct but incomplete.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Official Answer Key:
{answer_key}

Student's Submitted Answers:
{student_answers_str}

Please grade the submission.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        
        grading_result = llm.text_generation(prompt=grade_prompt, max_new_tokens=2048).strip()
        
        submissions_collection.insert_one({
            "assignment_id": assignment_id,
            "student_id": student_id,
            "submitted_answers": answers,
            "grading_result": grading_result,
            "submitted_at": datetime.now()
        })
        return grading_result

    @staticmethod
    def upload_pdf_for_summary(pdf_file, query):
        try:
            loader = PyPDFLoader(pdf_file)
            documents = loader.load_and_split(text_splitter=RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200))
            vectorstore = FAISS.from_documents(documents, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={'k': 5})
            
            template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a helpful assistant. Provide a concise summary of the document text and then answer the user's specific question based on it.<|eot_id|><|start_header_id|>user<|end_header_id|>
Document Text: {context}

User Query: {query}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
            
            rag_prompt = PromptTemplate.from_template(template)
            context_text = "\n\n".join([doc.page_content for doc in retriever.get_relevant_documents(query)])
            summary_response = llm.text_generation(prompt=rag_prompt.format(context=context_text, query=query), max_new_tokens=2048).strip()
            return summary_response
        except Exception as e:
            print(f"Error processing PDF for summary: {e}")
            return "Could not process the PDF file."


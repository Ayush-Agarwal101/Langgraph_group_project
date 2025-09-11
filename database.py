import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

load_dotenv()

try:
    CONNECTION_STRING = os.environ.get("MONGODB_URI")
    if not CONNECTION_STRING:
        raise ValueError("No MONGODB_URI found in environment variables.")
    
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully!")

except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    client = None

if client:
    db = client['college_management_db']
    # Core Collections
    users_collection = db['users']
    colleges_collection = db['colleges']
    study_material_chunks_collection = db['study_material_chunks']
    
    # New & Expanded Collections
    classes_collection = db['classes']
    enrollments_collection = db['enrollments']
    teachers_collection = db['teachers'] # Can be deprecated if we rely only on user role
    students_collection = db['students'] # Can be deprecated
    
    # Feature-specific Collections
    study_materials_collection = db['study_materials']
    assignments_collection = db['assignments']
    submissions_collection = db['submissions']
    attendance_collection = db['attendance']
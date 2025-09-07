import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

load_dotenv()

try:
    CONNECTION_STRING = os.environ.get("MONGODB_URI")
    if not CONNECTION_STRING:
        raise ValueError("No MONGODB_URI found in environment variables.")
    
    # tlsCAFile parameter tells PyMongo to use certifi's bundle of trusted certificates, which is required for a secure TLS/SSL connection to MongoDB Atlas.
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully!")

except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    client = None

if client:
    db = client['college_management_db']
    users_collection = db['users']
    colleges_collection = db['colleges']
    teachers_collection = db['teachers']
    students_collection = db['students']
    assignments_collection = db['assignments']
    submissions_collection = db['submissions']
    attendance_collection = db['attendance']
    student_vector_stores_collection = db['student_vector_stores']
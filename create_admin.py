# create_admin.py
import os
from passlib.hash import bcrypt
import uuid
from dotenv import load_dotenv

# This script is for ONE-TIME use to create the first admin user.

# Change these values to your desired admin credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "abcd1234"
ADMIN_NAME = "Administrator"

print("Attempting to create the first admin user...")

load_dotenv()
if not os.environ.get("MONGODB_URI"):
    print("❌ Critical Error: MONGODB_URI not found in .env file. Cannot connect to the database.")
else:
    try:
        from database import users_collection

        # 3. Check if an admin with this email already exists
        if users_collection.find_one({"email": ADMIN_EMAIL}):
            print(f"⚠️ An admin with the email '{ADMIN_EMAIL}' already exists. No action taken.")
        else:
            password_hash = bcrypt.hash(ADMIN_PASSWORD)

            admin_doc = {
                "_id": str(uuid.uuid4()),
                "name": ADMIN_NAME,
                "email": ADMIN_EMAIL,
                "_password_hash": password_hash,
                "role": "admin"
            }

            users_collection.insert_one(admin_doc)
            print("✅ Admin user created successfully!")
            print(f"   Email: {ADMIN_EMAIL}")
            print(f"   Password: {ADMIN_PASSWORD}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

    

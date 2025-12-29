
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.exception import AppwriteException

# Appwrite Configuration
ENDPOINT = "https://sfo.cloud.appwrite.io/v1"
PROJECT_ID = "6952e5ba002c94f9305c"
API_KEY = "standard_6525e0e8ab94269048e675e72adcef41c16cea7055fcfe72f4a8cc58a5a506a5de4f90eaf6d430edef3cb87a3fe7306eb170f91389e6546a17aaea8e376a5e273de7ad09fac05310e66357a8a504c06ac29e5d24d6b353784a1ea8d68ba28bbb4695d3bf9fe479f0700fd306b7ce34a7483f1f242f55da6cbb1a75589f0b6a59"
DATABASE_ID = "6952e5fa00389b56379c"

def setup_schema():
    client = Client()
    client.set_endpoint(ENDPOINT)
    client.set_project(PROJECT_ID)
    client.set_key(API_KEY)

    metrics_db = Databases(client)

    # 1. Create 'numbers' collection
    try:
        print("Creating 'numbers' collection...")
        metrics_db.create_collection(
            database_id=DATABASE_ID,
            collection_id='numbers',
            name='Numbers'
        )
        print("created 'numbers' collection")
    except AppwriteException as e:
        if e.code == 409:
            print("'numbers' collection already exists")
        else:
            print(f"Error creating 'numbers' collection: {e}")

    # Add attributes to 'numbers'
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'numbers', 'phone', 32, required=True)
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'numbers', 'status', 32, required=False, default='pending')
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'numbers', 'worker_id', 255, required=False)
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'numbers', 'result', 10000, required=False)
    except: pass
    # created_at is automatic in Appwrite, but we can add a custom one if needed. System $createdAt is usually enough.

    # 2. Create 'logs' collection
    try:
        print("Creating 'logs' collection...")
        metrics_db.create_collection(
            database_id=DATABASE_ID,
            collection_id='logs',
            name='Logs'
        )
        print("created 'logs' collection")
    except AppwriteException as e:
        if e.code == 409:
            print("'logs' collection already exists")
        else:
            print(f"Error creating 'logs' collection: {e}")

    # Add attributes to 'logs'
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'logs', 'number_id', 255, required=True)
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'logs', 'message', 10000, required=True)
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'logs', 'level', 32, required=False, default='info')
    except: pass
    try:
        metrics_db.create_string_attribute(DATABASE_ID, 'logs', 'screenshot_id', 255, required=False)
    except: pass
    
    # 3. Create indexes (Optional but good for performance)
    try:
        # Index for querying pending numbers
        metrics_db.create_index(DATABASE_ID, 'numbers', 'status_index', 'key', ['status'])
        print("Created status index on numbers")
    except: pass
    
    try:
        # Index for logs by number
        metrics_db.create_index(DATABASE_ID, 'logs', 'number_index', 'key', ['number_id'])
        print("Created number index on logs")
    except: pass

    print("Schema setup completed!")

if __name__ == "__main__":
    setup_schema()

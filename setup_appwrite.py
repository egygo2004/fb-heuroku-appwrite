
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.exception import AppwriteException

# Appwrite Configuration
ENDPOINT = "https://nyc.cloud.appwrite.io/v1"
PROJECT_ID = "6952e3ca0018a5ff10cd"
API_KEY = "standard_a688c78cfdb9f9e1c688b696e497fca8ad688b85fa74566694b4154a5e1dbf1654da46b529062042e33031516b3aef164361ae4cb58d977961af82382e54f26bb9f2dfd92e0b418a0cdfe66fcd2489d9600fdc3c8cf059934fa4658178d5cee855b91ded5ddb1a78208099527d9ae4873f2ab32e5b9f96823dc4389c9ce76f99"
DATABASE_ID = "6952e3fa00112ecd714f"

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

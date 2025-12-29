
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.permission import Permission
from appwrite.role import Role

# Appwrite Config
ENDPOINT = "https://sfo.cloud.appwrite.io/v1"
PROJECT_ID = "6952e5ba002c94f9305c"
API_KEY = "standard_6525e0e8ab94269048e675e72adcef41c16cea7055fcfe72f4a8cc58a5a506a5de4f90eaf6d430edef3cb87a3fe7306eb170f91389e6546a17aaea8e376a5e273de7ad09fac05310e66357a8a504c06ac29e5d24d6b353784a1ea8d68ba28bbb4695d3bf9fe479f0700fd306b7ce34a7483f1f242f55da6cbb1a75589f0b6a59"
DATABASE_ID = "6952e5fa00389b56379c"
COLLECTION_NUMBERS = "numbers"
COLLECTION_LOGS = "logs"

def fix_permissions():
    client = Client()
    client.set_endpoint(ENDPOINT)
    client.set_project(PROJECT_ID)
    client.set_key(API_KEY)
    
    db = Databases(client)
    
    # 1. Add missing 'timestamp' attribute to LOGS
    try:
        print("Adding 'timestamp' attribute to 'logs'...")
        # create_datetime_attribute(database_id, collection_id, key, required, x_default=None, array=False)
        # Note: using create_string_attribute if datetime causes issues with raw strings, but datetime is better.
        # Worker sends ISO string, so Datetime attribute is correct.
        db.create_datetime_attribute(DATABASE_ID, COLLECTION_LOGS, 'timestamp', required=False)
        print("Added 'timestamp' attribute.")
    except Exception as e:
        print(f"Error adding timestamp (might exist): {e}")

    # Wait a bit for attribute to be available? Appwrite is usually fast but indexing takes time.
    
    print("Updating permissions for 'numbers'...")
    try:
        db.update_collection(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_NUMBERS,
            name="Numbers",
            permissions=[
                Permission.read(Role.any()),
                Permission.create(Role.any()),
                Permission.update(Role.any()),
                Permission.delete(Role.any()),
                Permission.read(Role.guests()),
                Permission.create(Role.guests()),
                Permission.update(Role.guests()),
                Permission.delete(Role.guests())
            ]
        )
        print("Updated 'numbers' permissions.")
    except Exception as e:
        print(f"Error updating 'numbers': {e}")

    print("Updating permissions for 'logs'...")
    try:
        db.update_collection(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_LOGS,
            name="Logs",
            permissions=[
                Permission.read(Role.any()),
                Permission.create(Role.any()),
                Permission.update(Role.any()),
                Permission.delete(Role.any()),
                Permission.read(Role.guests()),
                Permission.create(Role.guests()),
                Permission.update(Role.guests()),
                Permission.delete(Role.guests())
            ]
        )
        print("Updated 'logs' permissions.")
    except Exception as e:
        print(f"Error updating 'logs': {e}")

if __name__ == "__main__":
    fix_permissions()

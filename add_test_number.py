
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
import os

# Appwrite Config
ENDPOINT = "https://sfo.cloud.appwrite.io/v1"
PROJECT_ID = "6952e5ba002c94f9305c"
API_KEY = "standard_6525e0e8ab94269048e675e72adcef41c16cea7055fcfe72f4a8cc58a5a506a5de4f90eaf6d430edef3cb87a3fe7306eb170f91389e6546a17aaea8e376a5e273de7ad09fac05310e66357a8a504c06ac29e5d24d6b353784a1ea8d68ba28bbb4695d3bf9fe479f0700fd306b7ce34a7483f1f242f55da6cbb1a75589f0b6a59"
DATABASE_ID = "6952e5fa00389b56379c"
COLLECTION_NUMBERS = "numbers"

from appwrite.query import Query

def list_pending():
    client = Client()
    client.set_endpoint(ENDPOINT)
    client.set_project(PROJECT_ID)
    client.set_key(API_KEY)
    
    db = Databases(client)
    
    try:
        result = db.list_documents(
            DATABASE_ID,
            COLLECTION_NUMBERS,
            queries=[
                Query.equal('status', 'pending')
            ]
        )
        print(f"Found {result['total']} pending numbers:")
        for doc in result['documents']:
            print(f"- {doc['phone']} (ID: {doc['$id']})")
    except Exception as e:
        print(f"Error listing numbers: {e}")

if __name__ == "__main__":
    list_pending()

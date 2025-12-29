
import os
import time
import sys
import glob
import asyncio
import subprocess
import logging
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.id import ID
from appwrite.query import Query
import requests

# Appwrite Config
ENDPOINT = "https://nyc.cloud.appwrite.io/v1"
PROJECT_ID = "6952e3ca0018a5ff10cd"
API_KEY = "standard_a688c78cfdb9f9e1c688b696e497fca8ad688b85fa74566694b4154a5e1dbf1654da46b529062042e33031516b3aef164361ae4cb58d977961af82382e54f26bb9f2dfd92e0b418a0cdfe66fcd2489d9600fdc3c8cf059934fa4658178d5cee855b91ded5ddb1a78208099527d9ae4873f2ab32e5b9f96823dc4389c9ce76f99"
DATABASE_ID = "6952e3fa00112ecd714f"
COLLECTION_NUMBERS = "numbers"
COLLECTION_LOGS = "logs"
BUCKET_ID = "6952e40d00390fd2b224"

# Heroku Config
HEROKU_API_KEY = os.environ.get('HEROKU_API_KEY')
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME', 'fb-mob-bot')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AppwriteWorker:
    def __init__(self):
        self.client = Client()
        self.client.set_endpoint(ENDPOINT)
        self.client.set_project(PROJECT_ID)
        self.client.set_key(API_KEY)
        self.db = Databases(self.client)
        self.storage = Storage(self.client)
        self.worker_id = os.environ.get('DYNO', 'local-worker')

    def log_to_appwrite(self, number_id, message, level='info', screenshot_path=None):
        """Log a message to Appwrite, optionally with a screenshot"""
        data = {
            'number_id': number_id,
            'message': message,
            'level': level,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        }

        # Upload screenshot if provided
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                with open(screenshot_path, 'rb') as f:
                    result = self.storage.create_file(
                        bucket_id=BUCKET_ID,
                        file_id=ID.unique(),
                        file=f
                    )
                    data['screenshot_id'] = result['$id']
            except Exception as e:
                logger.error(f"Failed to upload screenshot: {e}")

        try:
            self.db.create_document(DATABASE_ID, COLLECTION_LOGS, ID.unique(), data)
            logger.info(f"Logged to Appwrite: {message}")
        except Exception as e:
            logger.error(f"Failed to log to Appwrite: {e}")

    def get_pending_number(self):
        """Fetch a pending number from Appwrite"""
        try:
            result = self.db.list_documents(
                DATABASE_ID,
                COLLECTION_NUMBERS,
                queries=[
                    Query.equal('status', 'pending'),
                    Query.limit(1)
                ]
            )
            if result['documents']:
                return result['documents'][0]
        except Exception as e:
            logger.error(f"Error fetching pending number: {e}")
        return None

    def lock_number(self, document_id):
        """Update status to processing"""
        try:
            self.db.update_document(
                DATABASE_ID,
                COLLECTION_NUMBERS,
                document_id,
                {
                    'status': 'processing',
                    'worker_id': self.worker_id
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to lock number: {e}")
            return False

    def complete_number(self, document_id, status='completed', result_msg=None):
        """Update status to completed/failed"""
        data = {'status': status}
        if result_msg:
            data['result'] = result_msg
        
        try:
            self.db.update_document(
                DATABASE_ID,
                COLLECTION_NUMBERS,
                document_id,
                data
            )
        except Exception as e:
            logger.error(f"Error completing number: {e}")

    def restart_dyno(self):
        """Restart the Heroku dyno for IP rotation"""
        if not HEROKU_API_KEY:
            logger.warning("HEROKU_API_KEY not set, cannot restart dyno.")
            return

        logger.info("Triggering Dyno Restart for IP Rotation...")
        try:
            url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/dynos"
            headers = {
                "Authorization": f"Bearer {HEROKU_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.heroku+json; version=3"
            }
            requests.delete(url, headers=headers, timeout=10)
        except Exception as e:
            logger.error(f"Error restarting dyno: {e}")

    def get_current_ip(self):
        try:
            return requests.get('https://api.ipify.org', timeout=5).text
        except:
            return "Unknown"

    async def run_otp_script(self, number_doc):
        """Run the OTP browser script"""
        phone = number_doc['phone']
        doc_id = number_doc['$id']
        
        current_ip = self.get_current_ip()
        self.log_to_appwrite(doc_id, f"Worker {self.worker_id} started. IP: {current_ip}", 'info')

        # Create temp file for the number
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(phone)
            temp_path = f.name

        try:
            cmd = ['python', 'fb_otp_browser.py', temp_path, '--headless']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Monitor stdout for logs and current dir for screenshots
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                # Check for screenshot in log message (custom protocol required or just watch dir?)
                # fb_otp_browser currently logs: "Screenshot saved to: filename.png"
                
                level = 'info'
                if 'ERROR' in line.upper() or 'FAIL' in line.upper():
                    level = 'error'
                elif 'WARN' in line.upper():
                    level = 'warning'
                elif 'SUCCESS' in line.upper():
                    level = 'success'

                screenshot_file = None
                if "Screenshot saved to:" in line:
                    parts = line.split("Screenshot saved to:")
                    if len(parts) > 1:
                        potential_file = parts[1].strip()
                        if os.path.exists(potential_file):
                            screenshot_file = potential_file

                self.log_to_appwrite(doc_id, line, level, screenshot_file)
                
                # Cleanup uploaded screenshot locally
                if screenshot_file:
                    try:
                        os.remove(screenshot_file)
                    except: pass

            await process.wait()
            
            final_status = 'completed' if process.returncode == 0 else 'failed'
            self.complete_number(doc_id, final_status, f"Exit Code: {process.returncode}")

        except Exception as e:
            self.log_to_appwrite(doc_id, f"Critical Worker Error: {e}", 'error')
            self.complete_number(doc_id, 'failed', str(e))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def main_loop(self):
        logger.info(f"Worker {self.worker_id} started. Polling Appwrite...")
        
        while True:
            number_doc = self.get_pending_number()
            
            if number_doc:
                logger.info(f"Found number: {number_doc['phone']}")
                if self.lock_number(number_doc['$id']):
                    await self.run_otp_script(number_doc)
                    
                    # Restart after processing
                    self.restart_dyno()
                    return # Exit script, let Heroku restart happen
            
            # No numbers found? Sleep and retry
            logger.info("No pending numbers. Waiting 10s...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    worker = AppwriteWorker()
    asyncio.run(worker.main_loop())

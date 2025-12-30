
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
ENDPOINT = "https://sfo.cloud.appwrite.io/v1"
PROJECT_ID = "6952e5ba002c94f9305c" 
API_KEY = "standard_6525e0e8ab94269048e675e72adcef41c16cea7055fcfe72f4a8cc58a5a506a5de4f90eaf6d430edef3cb87a3fe7306eb170f91389e6546a17aaea8e376a5e273de7ad09fac05310e66357a8a504c06ac29e5d24d6b353784a1ea8d68ba28bbb4695d3bf9fe479f0700fd306b7ce34a7483f1f242f55da6cbb1a75589f0b6a59"
DATABASE_ID = "6952e5fa00389b56379c"
COLLECTION_NUMBERS = "numbers"
COLLECTION_LOGS = "logs"
BUCKET_ID = "6952e61e00371738e4bd"

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
        """Fetch a pending number from Appwrite (Randomized to reduce race conditions in cluster)"""
        try:
            # Fetch top 30 pending numbers
            result = self.db.list_documents(
                DATABASE_ID,
                COLLECTION_NUMBERS,
                queries=[
                    Query.equal('status', 'pending'),
                    Query.limit(30)
                ]
            )
            if result['documents']:
                import random
                # Pick a random one to minimize collision with other running workers
                return random.choice(result['documents'])
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

    async def send_telegram_photo(self, photo_path, caption=None):
        """Send photo to Telegram channel"""
        if not self.telegram_token or not self.chat_id:
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
            with open(photo_path, 'rb') as f:
                data = {'chat_id': self.chat_id, 'caption': caption}
                files = {'photo': f}
                requests.post(url, data=data, files=files, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")

    async def run_otp_script(self, number_doc):
        """Run the OTP browser script"""
        phone = number_doc['phone']
        doc_id = number_doc['$id']
        
        current_ip = self.get_current_ip()
        start_msg = f"🚀 **Worker {self.worker_id}**\n📱 Phone: `{phone}`\n🌐 IP: `{current_ip}`"
        self.log_to_appwrite(doc_id, f"Worker {self.worker_id} started. IP: {current_ip}", 'info')
        
        # We don't send start msg to telegram to reduce spam, only results

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

            # Monitor stdout for logs
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

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
                            # Send to Telegram immediately
                            await self.send_telegram_photo(screenshot_file, f"📸 `{phone}`\n{line}")

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
        logger.info(f"Worker {self.worker_id} started. Polling Appwrite (Batch Mode: 5)...")
        
        # Load Telegram Config from Env
        self.telegram_token = os.environ.get('TELEGRAM_TOKEN')
        self.chat_id = os.environ.get('CHAT_ID')

        processed_count = 0
        BATCH_SIZE = 8

        while True:
            # Check if we hit batch limit
            if processed_count >= BATCH_SIZE:
                logger.info(f"Batch limit ({BATCH_SIZE}) reached. Restarting for IP rotation...")
                self.restart_dyno()
                
                # preventing 'crashed' state by waiting for Heroku to kill us
                logger.info("Waiting for dyno restart...")
                await asyncio.sleep(60) 


            number_doc = self.get_pending_number()
            
            if number_doc:
                logger.info(f"Found number: {number_doc['phone']} ({processed_count + 1}/{BATCH_SIZE})")
                if self.lock_number(number_doc['$id']):
                    await self.run_otp_script(number_doc)
                    processed_count += 1
                    
                    # Small sleep between numbers in same batch
                    await asyncio.sleep(2)
                    continue 
            
            # Smart Retry Logic (User Request: 6-8 seconds random wait if fail/empty)
            import random
            wait_time = random.uniform(6, 8)
            logger.info(f"No pending numbers or fetch failed. Waiting {wait_time:.2f}s...")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    worker = AppwriteWorker()
    asyncio.run(worker.main_loop())

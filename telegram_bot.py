"""
Telegram Bot for FB OTP Automation
Runs fb_otp_browser.py directly on Heroku (no GitHub Actions)
With dyno restart after each number for IP rotation
"""

import os
import asyncio
import logging
import subprocess
import threading
import tempfile
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
ALLOWED_CHAT_ID = int(os.environ.get('CHAT_ID', '664193835'))
HEROKU_API_KEY = os.environ.get('HEROKU_API_KEY', '')
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME', 'fb-mob-bot')

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Track running process
running_process = None
process_lock = threading.Lock()


def get_current_ip():
    """Get current public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json().get('ip', 'Unknown')
    except:
        pass
    try:
        response = requests.get('https://ifconfig.me/ip', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return 'Unknown'


def get_pending_numbers():
    """Get pending numbers from Heroku config var"""
    try:
        pending = os.environ.get('PENDING_NUMBERS', '')
        if pending:
            return json.loads(pending)
    except:
        pass
    return []


def save_pending_numbers(numbers):
    """Save pending numbers to Heroku config var"""
    if not HEROKU_API_KEY:
        logger.error("HEROKU_API_KEY not set")
        return False
    
    try:
        url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars"
        headers = {
            "Authorization": f"Bearer {HEROKU_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.heroku+json; version=3"
        }
        data = {"PENDING_NUMBERS": json.dumps(numbers) if numbers else ""}
        resp = requests.patch(url, headers=headers, json=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Error saving pending numbers: {e}")
        return False


def restart_dyno():
    """Restart the Heroku dyno"""
    if not HEROKU_API_KEY:
        logger.error("HEROKU_API_KEY not set")
        return False
    
    try:
        url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/dynos"
        headers = {
            "Authorization": f"Bearer {HEROKU_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.heroku+json; version=3"
        }
        resp = requests.delete(url, headers=headers, timeout=10)
        return resp.status_code in [200, 202]
    except Exception as e:
        logger.error(f"Error restarting dyno: {e}")
        return False


def get_main_keyboard():
    """Return main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🚀 بدء الفحص", callback_data="start_otp")],
        [InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_otp")],
        [InlineKeyboardButton("🌐 عرض IP", callback_data="show_ip")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard():
    """Return confirmation keyboard after receiving numbers"""
    keyboard = [
        [InlineKeyboardButton("🚀 بدء الفحص الآن", callback_data="start_otp")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_selection")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def post_init(application):
    """Set up bot commands menu and check for pending numbers"""
    await application.bot.set_my_commands([
        BotCommand("start", "القائمة الرئيسية"),
        BotCommand("cancel", "إيقاف العملية الجارية"),
        BotCommand("ip", "عرض الـ IP الحالي"),
        BotCommand("help", "المساعدة")
    ])
    
    # Check for pending numbers after restart
    pending = get_pending_numbers()
    if pending:
        logger.info(f"Found {len(pending)} pending numbers after restart")
        current_ip = get_current_ip()
        
        # Send notification
        await application.bot.send_message(
            chat_id=ALLOWED_CHAT_ID,
            text=f"🔄 **تم إعادة التشغيل**\n\n"
                 f"🌐 IP الحالي: `{current_ip}`\n"
                 f"📱 الأرقام المتبقية: {len(pending)}\n\n"
                 f"⏳ جاري استكمال الفحص...",
            parse_mode='Markdown'
        )
        
        # Process next number
        asyncio.create_task(process_next_number(application.bot))


async def process_next_number(bot):
    """Process the next pending number"""
    pending = get_pending_numbers()
    
    if not pending:
        await bot.send_message(
            chat_id=ALLOWED_CHAT_ID,
            text="✅ **اكتملت جميع العمليات!**\n\nلا توجد أرقام متبقية.",
            parse_mode='Markdown'
        )
        return
    
    # Get next number
    current_number = pending[0]
    remaining = pending[1:]
    
    current_ip = get_current_ip()
    
    await bot.send_message(
        chat_id=ALLOWED_CHAT_ID,
        text=f"📱 **جاري فحص الرقم:**\n`{current_number}`\n\n"
             f"🌐 IP: `{current_ip}`\n"
             f"📊 المتبقي: {len(remaining)} رقم",
        parse_mode='Markdown'
    )
    
    # Save remaining numbers BEFORE processing (in case of crash)
    save_pending_numbers(remaining)
    
    # Process this number
    await run_single_number(bot, current_number)
    
    # If there are more numbers, restart dyno
    if remaining:
        await bot.send_message(
            chat_id=ALLOWED_CHAT_ID,
            text=f"🔄 جاري إعادة التشغيل للحصول على IP جديد...\n"
                 f"📱 الأرقام المتبقية: {len(remaining)}",
            parse_mode='Markdown'
        )
        restart_dyno()
    else:
        await bot.send_message(
            chat_id=ALLOWED_CHAT_ID,
            text="✅ **اكتملت جميع العمليات!**",
            parse_mode='Markdown'
        )


async def run_single_number(bot, phone_number):
    """Run OTP script for a single number using asyncio subprocess"""
    global running_process
    
    try:
        # Save number to temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(phone_number)
        temp_file.close()
        
        # Run the script using asyncio subprocess
        cmd = ['python', 'fb_otp_browser.py', temp_file.name, '--headless']
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        with process_lock:
            running_process = process
        
        # Read output line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line = line.decode('utf-8', errors='ignore').strip()
            if line:
                logger.info(f"[OTP] {line}")
                
                # Send important status updates (but not stats boxes)
                is_stats_line = any(c in line for c in ['║', '╔', '╚', '╠', '═'])
                is_important = any(kw in line.upper() for kw in ['OTP_SENT', 'NOT_FOUND', 'FAILED', 'ERROR', 'SUCCESS'])
                
                if is_important and not is_stats_line:
                    try:
                        await bot.send_message(chat_id=ALLOWED_CHAT_ID, text=f"📊 {line}")
                    except Exception as e:
                        logger.error(f"Error sending status: {e}")
        
        # Wait for process to complete
        await process.wait()
        logger.info(f"Process completed with exit code: {process.returncode}")
        
    except Exception as e:
        logger.error(f"Error running OTP script: {e}")
        try:
            await bot.send_message(chat_id=ALLOWED_CHAT_ID, text=f"❌ خطأ: {e}")
        except:
            pass
    finally:
        with process_lock:
            running_process = None
        try:
            os.remove(temp_file.name)
        except:
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        await update.message.reply_text("❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    current_ip = get_current_ip()
    
    reply_keyboard = [
        ["/start", "/cancel"],
        ["/ip", "/help"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        f"🤖 **مرحباً بك في بوت FB OTP**\n\n"
        f"🌐 IP الحالي: `{current_ip}`\n\n"
        f"📱 لإرسال الأرقام:\n"
        f"• أرسل ملف .txt يحتوي على الأرقام\n"
        f"• أو اكتب الأرقام مباشرة (كل رقم في سطر)\n\n"
        f"⚡ السكريبت يعيد التشغيل بعد كل رقم للحصول على IP جديد!",
        reply_markup=markup,
        parse_mode='Markdown'
    )


async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ip command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    current_ip = get_current_ip()
    await update.message.reply_text(f"🌐 **IP الحالي:**\n`{current_ip}`", parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    help_text = """❓ **المساعدة**

📱 **لإرسال الأرقام:**
• أرسل ملف .txt يحتوي على الأرقام
• أو اكتب الأرقام مباشرة (كل رقم في سطر)

📋 **الأوامر:**
/start - القائمة الرئيسية
/cancel - إيقاف العملية
/ip - عرض IP الحالي
/help - المساعدة

⚡ **طريقة العمل:**
• رقم واحد يُفحص
• ثم يتم إعادة تشغيل السيرفر
• IP جديد → الرقم التالي"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    global running_process
    
    # Clear pending numbers
    save_pending_numbers([])
    
    with process_lock:
        if running_process and running_process.poll() is None:
            running_process.terminate()
            running_process = None
            await update.message.reply_text("🛑 تم إيقاف العملية الجارية ومسح الأرقام المتبقية")
        else:
            await update.message.reply_text("✅ تم مسح الأرقام المتبقية")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received document"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ يرجى إرسال ملف .txt فقط")
        return
    
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    numbers_text = file_content.decode('utf-8')
    
    numbers = [line.strip() for line in numbers_text.split('\n') if line.strip() and not line.startswith('#')]
    
    if not numbers:
        await update.message.reply_text("❌ الملف فارغ")
        return
    
    context.user_data['pending_numbers'] = numbers
    current_ip = get_current_ip()
    
    await update.message.reply_text(
        f"✅ تم استلام **{len(numbers)}** رقم\n\n"
        f"🌐 IP الحالي: `{current_ip}`\n\n"
        f"🚀 اضغط 'بدء الفحص' للبدء:",
        reply_markup=get_confirm_keyboard(),
        parse_mode='Markdown'
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    text = update.message.text
    if text.startswith('/'):
        return
    
    numbers = [line.strip() for line in text.split('\n') if line.strip()]
    if not numbers:
        return
    
    context.user_data['pending_numbers'] = numbers
    current_ip = get_current_ip()
    
    await update.message.reply_text(
        f"✅ تم استلام **{len(numbers)}** رقم\n\n"
        f"🌐 IP الحالي: `{current_ip}`\n\n"
        f"🚀 اضغط 'بدء الفحص' للبدء:",
        reply_markup=get_confirm_keyboard(),
        parse_mode='Markdown'
    )


async def start_otp_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the OTP checking process"""
    query = update.callback_query
    
    if 'pending_numbers' not in context.user_data:
        await query.edit_message_text(
            "❌ لا توجد أرقام محفوظة. أرسل الأرقام أولاً.",
            reply_markup=get_main_keyboard()
        )
        return
    
    numbers = context.user_data.pop('pending_numbers')
    
    # Save all numbers to Heroku config
    if not save_pending_numbers(numbers):
        await query.edit_message_text(
            "❌ **خطأ:** لم يتم حفظ الأرقام.\n"
            "تأكد من إعداد HEROKU_API_KEY",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    current_ip = get_current_ip()
    
    await query.edit_message_text(
        f"🚀 **جاري بدء الفحص...**\n\n"
        f"📱 الأرقام: {len(numbers)}\n"
        f"🌐 IP الحالي: `{current_ip}`\n\n"
        f"🔄 سيتم إعادة التشغيل لبدء المعالجة...",
        parse_mode='Markdown'
    )
    
    # Restart dyno - the new process will pick up the numbers from config vars
    restart_dyno()



async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "start_otp":
        await start_otp_process(update, context)
    elif data == "cancel_otp":
        global running_process
        save_pending_numbers([])
        with process_lock:
            if running_process and running_process.poll() is None:
                running_process.terminate()
                running_process = None
        await query.edit_message_text("🛑 تم إيقاف العملية ومسح الأرقام", reply_markup=get_main_keyboard())
    elif data == "show_ip":
        current_ip = get_current_ip()
        await query.edit_message_text(f"🌐 **IP الحالي:**\n`{current_ip}`", parse_mode='Markdown', reply_markup=get_main_keyboard())
    elif data == "cancel_selection":
        if 'pending_numbers' in context.user_data:
            del context.user_data['pending_numbers']
        await query.edit_message_text("❌ تم إلغاء العملية", reply_markup=get_main_keyboard())
    elif data == "help":
        help_text = """❓ **المساعدة**

📱 لإرسال الأرقام: أرسل ملف .txt أو اكتب مباشرة

⚡ السيرفر يعيد التشغيل بعد كل رقم للحصول على IP جديد"""
        await query.edit_message_text(help_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')


def main():
    """Main function"""
    logger.info("Starting Telegram Bot...")
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set!")
        return
    
    # Build application
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("ip", ip_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot is running...")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

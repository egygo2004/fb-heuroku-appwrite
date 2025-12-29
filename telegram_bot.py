"""
Telegram Bot for FB OTP Automation
Runs fb_otp_browser.py directly on Heroku (no GitHub Actions)
"""

import os
import asyncio
import logging
import subprocess
import threading
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
ALLOWED_CHAT_ID = int(os.environ.get('CHAT_ID', '664193835'))

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Track running process
running_process = None
process_lock = threading.Lock()


def get_main_keyboard():
    """Return main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🚀 بدء الفحص", callback_data="start_otp")],
        [InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_otp")],
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
    """Set up bot commands menu"""
    await application.bot.set_my_commands([
        BotCommand("start", "القائمة الرئيسية"),
        BotCommand("cancel", "إيقاف العملية الجارية"),
        BotCommand("help", "المساعدة")
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        await update.message.reply_text("❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    reply_keyboard = [
        ["/start", "/cancel"],
        ["/help"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🤖 **مرحباً بك في بوت FB OTP**\n\n"
        "📱 لإرسال الأرقام:\n"
        "• أرسل ملف .txt يحتوي على الأرقام\n"
        "• أو اكتب الأرقام مباشرة (كل رقم في سطر)\n\n"
        "⚡ السكريبت يعمل مباشرة على Heroku!",
        reply_markup=markup,
        parse_mode='Markdown'
    )


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
/cancel - إيقاف العملية الجارية
/help - المساعدة

⚡ **طريقة العمل:**
السكريبت يعمل مباشرة على Heroku باستخدام Chrome Headless
النتائج تُرسل تلقائياً للمحادثة (صور + حالة)"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    global running_process
    
    with process_lock:
        if running_process and running_process.poll() is None:
            running_process.terminate()
            running_process = None
            await update.message.reply_text("🛑 تم إيقاف العملية الجارية")
        else:
            await update.message.reply_text("📭 لا توجد عمليات جارية")


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
    
    # Store numbers in context
    context.user_data['pending_numbers'] = numbers
    
    await update.message.reply_text(
        f"✅ تم استلام **{len(numbers)}** رقم\n\n"
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
    
    # Store numbers in context
    context.user_data['pending_numbers'] = numbers
    
    await update.message.reply_text(
        f"✅ تم استلام **{len(numbers)}** رقم\n\n"
        f"🚀 اضغط 'بدء الفحص' للبدء:",
        reply_markup=get_confirm_keyboard(),
        parse_mode='Markdown'
    )


def run_otp_script_sync(numbers_file: str, bot, chat_id: int, loop):
    """Run fb_otp_browser.py synchronously in a thread"""
    global running_process
    
    try:
        # Run the script with headless mode
        cmd = ['python', 'fb_otp_browser.py', numbers_file, '--headless', '--parallel']
        
        with process_lock:
            running_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        
        # Stream output
        output_lines = []
        for line in running_process.stdout:
            line = line.strip()
            if line:
                output_lines.append(line)
                logger.info(f"[OTP] {line}")
                
                # Send important status updates to Telegram
                if any(kw in line.upper() for kw in ['SUCCESS', 'OTP_SENT', 'NOT_FOUND', 'FAILED', 'ERROR']):
                    asyncio.run_coroutine_threadsafe(
                        bot.send_message(chat_id=chat_id, text=f"📊 {line}"),
                        loop
                    )
        
        running_process.wait()
        
        # Send completion message
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=chat_id,
                text="✅ **اكتملت العملية!**\n\nتم فحص جميع الأرقام.",
                parse_mode='Markdown'
            ),
            loop
        )
        
    except Exception as e:
        logger.error(f"Error running OTP script: {e}")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text=f"❌ خطأ: {e}"),
            loop
        )
    finally:
        with process_lock:
            running_process = None
        
        # Cleanup temp file
        try:
            os.remove(numbers_file)
        except:
            pass


async def start_otp_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the OTP checking process"""
    query = update.callback_query
    
    if 'pending_numbers' not in context.user_data:
        await query.edit_message_text(
            "❌ لا توجد أرقام محفوظة. أرسل الأرقام أولاً.",
            reply_markup=get_main_keyboard()
        )
        return
    
    global running_process
    with process_lock:
        if running_process and running_process.poll() is None:
            await query.edit_message_text(
                "⚠️ هناك عملية جارية بالفعل!\n"
                "استخدم /cancel لإيقافها أولاً.",
                reply_markup=get_main_keyboard()
            )
            return
    
    numbers = context.user_data.pop('pending_numbers')
    
    # Save numbers to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write('\n'.join(numbers))
    temp_file.close()
    
    await query.edit_message_text(
        f"🚀 **جاري بدء الفحص...**\n\n"
        f"📱 الأرقام: {len(numbers)}\n"
        f"⚡ الوضع: Headless + Parallel\n\n"
        f"📊 النتائج ستظهر هنا تلقائياً...",
        parse_mode='Markdown'
    )
    
    # Start in background thread
    loop = asyncio.get_event_loop()
    thread = threading.Thread(
        target=run_otp_script_sync,
        args=(temp_file.name, context.bot, query.message.chat_id, loop)
    )
    thread.daemon = True
    thread.start()


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "start_otp":
        await start_otp_process(update, context)
    elif data == "cancel_otp":
        global running_process
        with process_lock:
            if running_process and running_process.poll() is None:
                running_process.terminate()
                running_process = None
                await query.edit_message_text("🛑 تم إيقاف العملية", reply_markup=get_main_keyboard())
            else:
                await query.edit_message_text("📭 لا توجد عمليات جارية", reply_markup=get_main_keyboard())
    elif data == "cancel_selection":
        if 'pending_numbers' in context.user_data:
            del context.user_data['pending_numbers']
        await query.edit_message_text("❌ تم إلغاء العملية", reply_markup=get_main_keyboard())
    elif data == "help":
        help_text = """❓ **المساعدة**

📱 **لإرسال الأرقام:**
• أرسل ملف .txt يحتوي على الأرقام
• أو اكتب الأرقام مباشرة

⚡ السكريبت يعمل مباشرة على Heroku!"""
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
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot is running...")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

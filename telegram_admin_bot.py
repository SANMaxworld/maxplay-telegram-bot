# MaxPlay Telegram Admin Bot - Render
# Using python-telegram-bot (HTTP API, not MTProto)
# No time sync issues, much simpler

import os
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import firebase_admin
from firebase_admin import credentials, db

# ============ LOGGING ============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramBot")

# ============ FIREBASE SETUP ============

try:
    firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_credentials_json:
        raise ValueError("FIREBASE_CREDENTIALS not set")
    
    firebase_creds = json.loads(firebase_credentials_json)
    cred = credentials.Certificate(firebase_creds)
    
    try:
        firebase_app = firebase_admin.get_app()
    except:
        firebase_app = firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://mwhub-proxy.firebaseio.com'
        })
    
    logger.info("✅ Firebase initialized successfully")
except Exception as e:
    logger.error(f"❌ Firebase init error: {e}")
    raise

# ============ CONFIG ============

try:
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    else:
        ADMIN_IDS = []
    logger.info(f"✅ Admin IDs loaded: {ADMIN_IDS}")
except Exception as e:
    logger.error(f"❌ Admin IDs error: {e}")
    ADMIN_IDS = []

try:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set")
    logger.info(f"✅ Bot token loaded: {BOT_TOKEN[:20]}...")
except Exception as e:
    logger.error(f"❌ Bot token error: {e}")
    raise

MANAGER_URL = os.getenv("MANAGER_URL", "https://nawazkhan001-mw-hub-master.hf.space")

logger.info(f"✅ Manager URL: {MANAGER_URL}")
logger.info(f"🤖 Bot mode: python-telegram-bot (HTTP API, no MTProto)")

# ============ FIREBASE HELPERS ============

def get_active_bots():
    """Get all active bots from Firebase"""
    try:
        bots_ref = db.reference("bots")
        bots = bots_ref.get()
        
        if not bots or bots is None:
            logger.info("No bots in database yet")
            return []
        
        active_bots = []
        now = datetime.now().timestamp()
        
        for bot_id, bot_data in bots.items():
            if bot_data is None:
                continue
            last_heartbeat = bot_data.get("last_heartbeat", 0)
            if (now - last_heartbeat) < 60:
                active_bots.append({
                    "id": bot_id,
                    **bot_data
                })
        
        logger.info(f"✅ Got {len(active_bots)} active bots")
        return sorted(active_bots, key=lambda x: x.get("used_count", 0))
    
    except Exception as e:
        logger.error(f"Error getting bots: {e}")
        return []

def get_videos():
    """Get all videos from Firebase"""
    try:
        videos_ref = db.reference("videos")
        videos = videos_ref.get() or {}
        return videos
    except Exception as e:
        logger.error(f"Error getting videos: {e}")
        return {}

def save_video(video_id: str, file_id: str, file_name: str, file_size: int, uploaded_by: int):
    """Save video to Firebase"""
    try:
        db.reference(f"videos/{video_id}").set({
            "title": file_name,
            "file_id": file_id,
            "size": file_size,
            "uploaded_by": uploaded_by,
            "created_at": datetime.now().isoformat()
        })
        logger.info(f"✅ Video saved: {video_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving video: {e}")
        return False

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        logger.warning(f"⚠️  Unauthorized user: {user_id}")
        await update.message.reply_text("❌ Unauthorized access")
        return
    
    await update.message.reply_text(
        "👋 Welcome to MaxPlay Admin Bot\n\n"
        "Available commands:\n"
        "/stats - System statistics\n"
        "/list_bots - List all bots\n"
        "/health - System health\n"
        "/videos - Uploaded videos\n\n"
        "Or: Forward a video file to upload"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats command"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    logger.info(f"✅ Processing /stats from user {user_id}")
    
    bots = get_active_bots()
    videos = get_videos()
    
    text = f"📊 **System Statistics**\n\n"
    text += f"🤖 Active Bots: {len(bots)}\n"
    text += f"💾 Total Capacity: {len(bots) * 3}\n"
    text += f"📹 Total Videos: {len(videos)}\n"
    text += f"📊 Used Today: {sum([b.get('used_count', 0) for b in bots])}\n\n"
    text += f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"✅ Sent /stats response")

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List bots command"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    logger.info(f"✅ Processing /list_bots from user {user_id}")
    
    try:
        bots_data = db.reference("bots").get() or {}
    except:
        bots_data = {}
    
    text = f"🤖 **Bot List** ({len(bots_data)} total)\n\n"
    
    if not bots_data:
        text += "❌ No bots registered yet\n\n"
        text += "Waiting for Space 1-2 workers to connect..."
    else:
        for bot_id, bot_data in list(bots_data.items())[:15]:
            if bot_data is None:
                continue
            status = "🟢" if bot_data.get("status") == "active" else "🔴"
            text += f"{status} {bot_id}\n"
            text += f"   Used: {bot_data.get('used_count', 0)}/{bot_data.get('capacity', 3)}\n"
            text += f"   Platform: {bot_data.get('platform')}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"✅ Sent /list_bots response")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health command"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    logger.info(f"✅ Processing /health from user {user_id}")
    
    bots = get_active_bots()
    text = "🏥 **System Health**\n\n"
    text += f"✅ Manager: Online\n"
    text += f"✅ Firebase: Connected\n"
    text += f"✅ Admin Bot: Running (Render)\n"
    text += f"✅ Active Bots: {len(bots)}\n"
    text += f"✅ API: Running\n\n"
    text += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"✅ Sent /health response")

async def videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Videos command"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    logger.info(f"✅ Processing /videos from user {user_id}")
    
    videos_data = get_videos()
    
    text = f"📹 **Uploaded Videos** ({len(videos_data)})\n\n"
    
    if not videos_data:
        text += "❌ No videos uploaded yet\n\n"
        text += "Forward a video file to upload"
    else:
        for video_id, video_data in list(videos_data.items())[:10]:
            if video_data is None:
                continue
            title = video_data.get('title', 'Unknown')[:30]
            text += f"• {title}\n"
            text += f"  `{video_id}`\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"✅ Sent /videos response")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document/video upload"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    try:
        document = update.message.document
        file_id = document.file_id
        file_name = document.file_name
        file_size = document.file_size or 0
        
        logger.info(f"📹 Processing video upload: {file_name} ({file_size} bytes)")
        
        video_id = file_name.replace(" ", "_").replace(".mp4", "").replace(".mkv", "").replace(".avi", "").replace(".mov", "")
        
        # Save to Firebase
        success = save_video(video_id, file_id, file_name, file_size, user_id)
        
        if success:
            text = f"✅ **Video Saved**\n\n"
            text += f"📝 Title: {file_name}\n"
            text += f"🎬 ID: `{video_id}`\n"
            text += f"💾 Size: {file_size / (1024**3):.2f} GB\n\n"
            text += f"Ready for streaming!"
            
            await update.message.reply_text(text, parse_mode="Markdown")
            logger.info(f"✅ Video uploaded and saved: {video_id}")
        else:
            await update.message.reply_text("❌ Failed to save video to database")
            logger.error(f"❌ Failed to save video: {video_id}")
    
    except Exception as e:
        logger.error(f"❌ Document processing error: {e}")
        await update.message.reply_text(f"❌ Upload error: {str(e)[:100]}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    logger.info(f"📨 Text message from {user_id}")
    
    await update.message.reply_text(
        "📝 Use commands:\n\n"
        "/stats - Statistics\n"
        "/list_bots - List bots\n"
        "/health - Health check\n"
        "/videos - Videos\n\n"
        "Or: Forward a video file to upload"
    )

# ============ MAIN ============

async def main():
    """Start the bot"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Telegram Admin Bot STARTING on Render")
        logger.info("=" * 60)
        logger.info(f"✅ Firebase: Connected")
        logger.info(f"✅ Bot: Ready")
        logger.info(f"✅ Admin IDs: {ADMIN_IDS}")
        logger.info(f"✅ Manager: {MANAGER_URL}")
        logger.info("=" * 60)
        logger.info("📝 Commands:")
        logger.info("   /stats - System statistics")
        logger.info("   /list_bots - List all bots")
        logger.info("   /health - System health")
        logger.info("   /videos - Uploaded videos")
        logger.info("   Forward file - Upload video")
        logger.info("=" * 60)
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("list_bots", list_bots))
        application.add_handler(CommandHandler("health", health))
        application.add_handler(CommandHandler("videos", videos))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        logger.info("✅ Bot handlers registered")
        logger.info("✅ Bot polling started...")
        
        # Start polling
        await application.run_polling()
    
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    
    logger.info("Starting bot...")
    asyncio.run(main())
    

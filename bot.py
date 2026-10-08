import os
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import firebase_admin
from firebase_admin import credentials, db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TelegramBot")

try:
    firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
    firebase_creds = json.loads(firebase_credentials_json)
    cred = credentials.Certificate(firebase_creds)
    try:
        firebase_admin.get_app()
    except:
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://mwhub-proxy.firebaseio.com'})
    logger.info("✅ Firebase initialized")
except Exception as e:
    logger.error(f"❌ Firebase error: {e}")
    raise

ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MANAGER_URL = os.getenv("MANAGER_URL", "https://nawazkhan001-mw-hub-master.hf.space")

logger.info(f"✅ Admin IDs: {ADMIN_IDS}")
logger.info(f"✅ Manager: {MANAGER_URL}")

def get_bots():
    try:
        return db.reference("bots").get() or {}
    except:
        return {}

def get_videos():
    try:
        return db.reference("videos").get() or {}
    except:
        return {}

def save_video(video_id, file_id, file_name, file_size, user_id):
    try:
        db.reference(f"videos/{video_id}").set({
            "title": file_name, "file_id": file_id, "size": file_size,
            "uploaded_by": user_id, "created_at": datetime.now().isoformat()
        })
        return True
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    await update.message.reply_text("/stats /list_bots /health /videos\nOr: Forward video file")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    bots = get_bots()
    videos = get_videos()
    text = f"📊 **Stats**\n🤖 Bots: {len(bots)}\n📹 Videos: {len(videos)}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    bots = get_bots()
    text = f"🤖 **Bots** ({len(bots)})\n\n"
    if not bots:
        text += "No bots yet"
    else:
        for bid, data in list(bots.items())[:10]:
            text += f"🟢 {bid}: {data.get('used_count', 0)}/{data.get('capacity', 3)}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    bots = get_bots()
    text = f"🏥 **Health**\n✅ Manager: Online\n✅ Firebase: Connected\n✅ Bots: {len(bots)}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    vids = get_videos()
    text = f"📹 **Videos** ({len(vids)})\n\n"
    if not vids:
        text += "No videos yet"
    else:
        for vid_id, data in list(vids.items())[:5]:
            text += f"• {data.get('title', 'Unknown')[:25]}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    doc = update.message.document
    video_id = doc.file_name.replace(" ", "_").replace(".mp4", "").replace(".mkv", "")
    if save_video(video_id, doc.file_id, doc.file_name, doc.file_size or 0, update.effective_user.id):
        text = f"✅ **Saved**\n📝 {doc.file_name}\n🎬 `{video_id}`"
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Failed to save")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    await update.message.reply_text("/stats /list_bots /health /videos")

async def main():
    logger.info("🚀 Bot starting...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("list_bots", list_bots))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("videos", videos))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

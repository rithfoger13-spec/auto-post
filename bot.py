import os
import logging
import requests
import aiohttp
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# បើកដំណើរការ Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8909903351:AAEvmhToP2-Vf0lqpA_wXNdXsBoAw5rc5jM"

os.makedirs("downloads", exist_ok=True)

# ==========================================
# Dummy HTTP Server សម្រាប់ Render Web Service (ការពារកំហុស No open ports)
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    logger.info(f"🌐 Dummy HTTP Server running on port {port}")
    server.serve_forever()

# ==========================================
# មុខងារទាញយកទាំង Slideshow និង វីដេអូធម្មតា ព្រមទាំង Caption & Hashtags
# ==========================================
async def process_single_link(update: Update, url: str):
    await update.message.reply_text("🔍 កំពុងពិនិត្យ និងទាញយកទិន្នន័យពី TikTok...")
    
    api_url = f"https://www.tikwm.com/api/?url={url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                
        if data.get("code") == 0:
            info = data.get("data", {})
            images = info.get("images", [])
            video_url = info.get("play", "")
            title = info.get("title", "No caption")
            
            # ករណីទី ១៖ ប្រសិនបើជា Slideshow (រូបភាពច្រើនសន្លឹក)
            if images:
                await update.message.reply_text("🔥 **រកឃើញ Slideshow!**\n🖼 កំពុងទាញយករូបភាព និងអត្ថបទផ្ញើជូន...")

                media_group = []
                for idx, img_url in enumerate(images[:10]):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(img_url) as img_resp:
                            if img_resp.status == 200:
                                img_data = await img_resp.read()
                                
                                if idx == 0:
                                    media_group.append(InputMediaPhoto(media=img_data, caption=f"📦 **TikTok Slideshow & Caption:**\n\n{title}", parse_mode="Markdown"))
                                else:
                                    media_group.append(InputMediaPhoto(media=img_data))
                                
                if media_group:
                    await update.message.reply_chat_action("upload_photo")
                    await update.message.reply_media_group(media=media_group)
                    await update.message.reply_text("✅ រួចរាល់! Slideshow ត្រូវបានទាញយកដោយជោគជ័យ។")
                else:
                    await update.message.reply_text("⚠️ មិនអាចទាញយករូបភាពពី Slideshow នេះបានទេ។")

            # ករណីទី ២៖ ប្រសិនបើជាវីដេអូធម្មតា (Video)
            elif video_url:
                await update.message.reply_text("🎬 **រកឃើញវីដេអូធម្មតា!**\n📥 កំពុងទាញយកវីដេអូ និងអត្ថបទផ្ញើជូន...")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(video_url) as vid_resp:
                        if vid_resp.status == 200:
                            vid_data = await vid_resp.read()
                            await update.message.reply_chat_action("upload_video")
                            await update.message.reply_video(
                                video=vid_data,
                                caption=f"🎬 **TikTok Video & Caption:**\n\n{title}",
                                parse_mode="Markdown"
                            )
                            await update.message.reply_text("✅ រួចរាល់! វីដេអូត្រូវបានទាញយកដោយជោគជ័យ។")
                        else:
                            await update.message.reply_text("⚠️ មិនអាចទាញយកឯកសារវីដេអូនេះបានទេ។")
            else:
                await update.message.reply_text("❌ មិនអាចរកឃើញមាតិកា (រូបភាព ឬវីដេអូ) ពី Link នេះបានទេ។")
        else:
            await update.message.reply_text("❌ មិនអាចអាន Link នេះបានទេ (ប្រហែលខុសទម្រង់ ឬជាប់កម្រិតឯកជនភាព)។")
            
    except Exception as e:
        await update.message.reply_text(f"❌ មានបញ្ហាបច្ចេកទេស៖ {str(e)}")

# ==========================================
# Message Handler
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_url = update.message.text
    if not raw_url.startswith("http"):
        await update.message.reply_text("👋 សូមផ្ញើ Link TikTok (Slideshow ឬ Video) មកកាន់ខ្ញុំ!")
        return

    try:
        response = requests.head(raw_url, allow_redirects=True, timeout=5)
        real_url = response.url
    except Exception:
        real_url = raw_url

    await process_single_link(update, real_url)

def main():
    # ចាប់ផ្តើម Dummy HTTP Server ក្នុង Thread ដាច់ដោយឡែក ដើម្បីបើក Port ឱ្យ Render ស្គាល់
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 Bot Universal Download (Video + Slideshow + Caption) កំពុងដំណើរការហើយ...")
    application.run_polling()

if __name__ == '__main__':
    main()

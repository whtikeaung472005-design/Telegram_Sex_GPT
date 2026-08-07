import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot
from bot_logic import dp, bot
from dotenv import load_dotenv
from bot_logic import setup_bot_commands

# Logging ကို သေချာ setup လုပ်ထားမှ error တွေကို ခြေရာခံလို့ရမယ်
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

PORT = int(os.getenv("PORT", 10000))

async def health_check(request):
    """UptimeRobot အတွက် Health Check Endpoint"""
    return web.Response(text="Bot and Web Server are running smoothly!", status=200)

async def start_web_server():
    """aiohttp Web Server ကို ပိုမိုခိုင်မာအောင် တည်ဆောက်ခြင်း"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"[Web Server] Started on http://0.0.0.0:{PORT}")
    except Exception as e:
        logger.error(f"[Web Server] Failed to start: {e}")

async def main():
    """Bot နှင့် Web Server ကို အကောင်းဆုံး ပေါင်းစပ် Run ခြင်း"""
    logger.info("[System] Initializing Services...")
    
    # Web Server ကို background မှာ run မယ်
    server_task = asyncio.create_task(start_web_server())
    
    try:
        logger.info("[Telegram Bot] Starting polling...")
        # Bot commands တွေကို အရင် setup လုပ်မယ်
        await setup_bot_commands(bot)
        # Webhook တွေကို ဖျက်ပြီး update အသစ်ကနေ စမယ်
        await bot.delete_webhook(drop_pending_updates=True) 
        
        # Bot polling ကို စတင်မယ်
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"[Telegram Bot] Critical Error: {e}")
    finally:
        # Bot session ကို ပိတ်ပြီးမှ server task ကို ပိတ်မယ်
        await bot.session.close()
        server_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("[System] Shutting down gracefully.")

# Filename: main.py
import os
import asyncio
from aiohttp import web
from aiogram import Bot
from bot_logic import dp, bot
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 10000))

async def health_check(request):
    """
    UptimeRobot မှ Server အသက်ရှင်/မရှင် လာစစ်မည့် Endpoint.
    200 OK ပြန်ပေးမှသာ Render မှ Sleep မဖြစ်အောင် တားဆီးနိုင်မည်။
    """
    return web.Response(text="Bot and Web Server are running smoothly!", status=200)

async def start_web_server():
    """aiohttp Web Server ကို ဖန်တီးခြင်း"""
    app = web.Application()
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    # 0.0.0.0 is crucial for Render deployment
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"[Web Server] Started on http://0.0.0.0:{PORT}")

async def main():
    """Bot Long-polling နှင့် Web Server ကို ပြိုင်တူ (Concurrently) Run ခြင်း"""
    print("[System] Initializing Services...")
    
    # Start Web Server as a background task
    asyncio.create_task(start_web_server())
    
    # Start Telegram Bot Long-Polling
    try:
        print("[Telegram Bot] Starting polling...")
        # Skip updates that happened while bot was offline
        await bot.delete_webhook(drop_pending_updates=True) 
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("[System] Shutting down gracefully.")
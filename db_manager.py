# Filename: db_manager.py
import os
import time
import aiohttp
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Plan limits configuration (Seconds)
FREE_RESET_SECONDS = 8 * 3600  
PRO_RESET_SECONDS = 4 * 3600   

FREE_MSG_LIMIT = 20
PRO_MSG_LIMIT = 100

FREE_CHAR_LIMIT = 1000
PRO_CHAR_LIMIT = 8000

# ... (get_or_create_user, _check_and_reset_limits, check_usage_allowed, update_usage function များကို မူလအတိုင်း ထားပါ) ...

async def save_chat(telegram_id: int, role: str, content: str) -> None:
    """အသုံးပြုသူ (user) သို့မဟုတ် AI (assistant) ၏ စကားကို Database တွင် သိမ်းဆည်းရန်"""
    url = f"{SUPABASE_URL}/rest/v1/chat_history"
    data = {
        "telegram_id": telegram_id,
        "role": role,
        "content": content
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, headers=HEADERS, json=data)

async def get_chat_history(telegram_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """နောက်ဆုံးပြောခဲ့သော စကား (၁၀) ကြိမ်ကို Database မှ အချိန်စဉ်ဆက်အတိုင်း ဆွဲထုတ်ရန်"""
    # created_at အလိုက် အသစ်ဆုံးကို အရင်ယူမည် (order=created_at.desc)
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}&order=created_at.desc&limit={limit}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                # OpenRouter သို့ပို့ရန် မှန်ကန်သော format အဖြစ် ပြောင်းလဲခြင်း
                history = [{"role": row["role"], "content": row["content"]} for row in data]
                # API သို့ ပို့သောအခါ အဟောင်းမှ အသစ်သို့ စဉ်ထားရန် လိုသဖြင့် List ကို ပြောင်းပြန်လှန်ပါမည်
                return history[::-1] 
            return []

async def clear_history(telegram_id: int) -> bool:
    """New Chat စတင်ရန်အတွက် ယခင် မှတ်ဉာဏ်များကို ဖျက်ပစ်ရန်"""
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=HEADERS) as response:
            return response.status in (200, 204)

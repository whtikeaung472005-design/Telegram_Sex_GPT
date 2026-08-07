# Filename: db_manager.py
import os
import time
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

FREE_RESET_SECONDS = 8 * 3600
PRO_RESET_SECONDS = 4 * 3600
FREE_MSG_LIMIT = 20
PRO_MSG_LIMIT = 100
FREE_CHAR_LIMIT = 1000
PRO_CHAR_LIMIT = 8000

async def get_session():
    from ai_service import get_session as ai_get_session
    return await ai_get_session()

async def get_or_create_user(telegram_id: int):
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}.select()"
    session = await get_session()
    async with session.get(url, headers=HEADERS) as response:
        if response.status != 200 or not (await response.json()):
            create_url = f"{SUPABASE_URL}/rest/v1/users"
            data = {"telegram_id": telegram_id, "plan_type": "free", "message_count": 0, "last_reset": int(time.time())}
            await session.post(create_url, headers=HEADERS, json=data)

async def check_usage_allowed(telegram_id: int) -> tuple:
    """(is_allowed, reason, char_limit)"""
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}.select()"
    session = await get_session()
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        if not data: return False, "User not found", 0
        
        user = data[0]
        plan = user.get('plan_type', 'free')
        count = user.get('message_count', 0)
        last_reset = user.get('last_reset', 0)
        
        now = int(time.time())
        reset_time = FREE_RESET_SECONDS if plan == 'free' else PRO_RESET_SECONDS
        limit = FREE_MSG_LIMIT if plan == 'free' else PRO_MSG_LIMIT
        char_limit = FREE_CHAR_LIMIT if plan == 'free' else PRO_CHAR_LIMIT

        if now - last_reset > reset_time:
            update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
            await session.patch(update_url, headers=HEADERS, json={"message_count": 0, "last_reset": now})
            count = 0

        if count >= limit:
            return False, "Limit exceeded", char_limit
        
        return True, "Allowed", char_limit

async def update_usage(telegram_id: int, char_count: int):
    # message_count ကို ၁ တိုးပေးဖို့အတွက် အရင်ဆုံး လက်ရှိ count ကို ယူရမယ်
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}.select()"
    session = await get_session()
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        if data:
            current_count = data[0].get('message_count', 0)
            update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
            await session.patch(update_url, headers=HEADERS, json={"message_count": current_count + 1})

async def save_chat(telegram_id: int, role: str, content: str):
    url = f"{SUPABASE_URL}/rest/v1/chat_history"
    data = {"telegram_id": telegram_id, "role": role, "content": content}
    session = await get_session()
    await session.post(url, headers=HEADERS, json=data)

async def get_chat_history(telegram_id: int, limit: int = 10) -> List[Dict[str, str]]:
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}&order=created_at.desc&limit={limit}"
    session = await get_session()
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            return [{"role": row["role"], "content": row["content"]} for row in data][::-1]
        return []

async def clear_history(telegram_id: int) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}"
    session = await get_session()
    async with session.delete(url, headers=HEADERS) as response:
        return response.status in (200, 204)

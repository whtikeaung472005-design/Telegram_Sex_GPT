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

# Supabase API အတွက် Header များ
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- Plan Limits Configuration ---
FREE_RESET_SECONDS = 8 * 3600  # 8 Hours
PRO_RESET_SECONDS = 4 * 3600    # 4 Hours

FREE_MSG_LIMIT = 20
PRO_MSG_LIMIT = 100

FREE_CHAR_LIMIT = 1000
PRO_CHAR_LIMIT = 8000

async def get_session():
    """ai_service.py မှ global session ကို ယူသုံးရန်"""
    from ai_service import get_session as ai_get_session
    return await ai_get_session()

async def get_or_create_user(telegram_id: int):
    """User ရှိမရှိ စစ်ဆေးပြီး မရှိလျှင် အသစ်ဆောက်ရန်"""
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    session = await get_session()
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                if not data or len(data) == 0:
                    create_url = f"{SUPABASE_URL}/rest/v1/users"
                    payload = {
                        "telegram_id": telegram_id, 
                        "plan_type": "free", 
                        "message_count": 0, 
                        "last_reset": int(time.time()),
                        "pro_expiry_date": 0
                    }
                    await session.post(create_url, headers=HEADERS, json=payload)
                    logger.info(f"[DB] Created new user: {telegram_id}")
    except Exception as e:
        logger.error(f"[DB] Exception in get_or_create_user: {str(e)}")

async def check_usage_allowed(telegram_id: int) -> tuple:
    """အသုံးပြုခွင့် ရှိမရှိ နှင့် စာလုံးရေ limit ကို စစ်ဆေးရန် (is_allowed, reason, char_limit)"""
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    session = await get_session()
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                logger.error(f"[DB] Supabase error: {response.status}")
                return False, "Supabase Error", 0
                
            data = await response.json()
            if not data or len(data) == 0:
                await get_or_create_user(telegram_id)
                return True, "New user created", FREE_CHAR_LIMIT
            
            user = data[0]
            plan = user.get('plan_type', 'free')
            expiry_date = user.get('pro_expiry_date', 0)
            now = int(time.time())

            # 1. Pro သက်တမ်းကုန်မကုန် စစ်ဆေးခြင်း
            if plan == 'pro' and expiry_date != 0 and now > expiry_date:
                # သက်တမ်းကုန်သွားပြီ ဖြစ်သောကြောင့် free ပြန်ပြောင်းမည်
                update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
                await session.patch(update_url, headers=HEADERS, json={"plan_type": "free"})
                plan = 'free'
                logger.info(f"[DB] User {telegram_id} Pro plan expired. Reverted to free.")

            # 2. Plan အလိုက် Limit များ သတ်မှတ်ခြင်း
            count = user.get('message_count', 0)
            last_reset = user.get('last_reset', 0)
            
            reset_time = FREE_RESET_SECONDS if plan == 'free' else PRO_RESET_SECONDS
            limit = FREE_MSG_LIMIT if plan == 'free' else PRO_MSG_LIMIT
            char_limit = FREE_CHAR_LIMIT if plan == 'free' else PRO_CHAR_LIMIT

            # 3. Reset Time ပြည့်မပြည့် စစ်ဆေးပြီး Count ကို ၀ ပြန်လုပ်ခြင်း
            if now - last_reset > reset_time:
                update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
                await session.patch(update_url, headers=HEADERS, json={"message_count": 0, "last_reset": now})
                count = 0

            # 4. Message Limit ပြည့်မပြည့် စစ်ဆေးခြင်း
            if count >= limit:
                return False, "Limit exceeded", char_limit
            
            return True, "Allowed", char_limit
    except Exception as e:
        logger.exception(f"[DB] CRITICAL ERROR in check_usage_allowed: {str(e)}")
        return False, "Database Exception", 0

async def update_usage(telegram_id: int, char_count: int):
    """မေးခွန်းအရေအတွက် (Message Count) ကို ၁ တိုးပေးရန်"""
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    session = await get_session()
    try:
        async with session.get(url, headers=HEADERS) as response:
            data = await response.json()
            if data and len(data) > 0:
                current_count = data[0].get('message_count', 0)
                await session.patch(url, headers=HEADERS, json={"message_count": current_count + 1})
    except Exception as e:
        logger.error(f"[DB] Error in update_usage: {e}")

async def set_user_plan(telegram_id: int, plan: str):
    """Admin မှ User ၏ Plan ကို ပြောင်းလဲရန် (သက်တမ်း တစ်လ သတ်မှတ်ချက် ပါဝင်သည်)"""
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    session = await get_session()
    try:
        now = int(time.time())
        payload = {"plan_type": plan, "message_count": 0}
        
        if plan == "pro":
            # ရက်ပေါင်း ၃၀ သက်တမ်း သတ်မှတ်ခြင်း (30 days * 24h * 60m * 60s)
            expiry_timestamp = now + (30 * 24 * 60 * 60)
            payload["pro_expiry_date"] = expiry_timestamp
        else:
            payload["pro_expiry_date"] = 0

        await session.patch(url, headers=HEADERS, json=payload)
        return True
    except Exception as e:
        logger.error(f"[DB] Error in set_user_plan: {e}")
        return False

async def save_chat(telegram_id: int, role: str, content: str):
    """Chat History ကို Database တွင် သိမ်းဆည်းရန်"""
    url = f"{SUPABASE_URL}/rest/v1/chat_history"
    data = {"telegram_id": telegram_id, "role": role, "content": content}
    session = await get_session()
    try:
        await session.post(url, headers=HEADERS, json=data)
    except Exception as e:
        logger.error(f"[DB] Error in save_chat: {e}")

async def get_chat_history(telegram_id: int, limit: int = 20) -> List[Dict[str, str]]:
    """Conversation History နောက်ဆုံး ၂၀ ကို အချိန်စဉ်ဆက်အတိုင်း ဆွဲထုတ်ရန်"""
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}&order=created_at.desc&limit={limit}"
    session = await get_session()
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                # ပို့လိုက်တဲ့ data က အသစ်ဆုံးကနေ အဟောင်းကို စီထားတာမို့ ပြောင်းပြန်လှန်ပေးရမယ်
                return [{"role": row["role"], "content": row["content"]} for row in data][::-1]
    except Exception as e:
        logger.error(f"[DB] Error in get_chat_history: {e}")
    return []

async def clear_history(telegram_id: int) -> bool:
    """Chat History အားလုံးကို ဖျက်ရန်"""
    url = f"{SUPABASE_URL}/rest/v1/chat_history?telegram_id=eq.{telegram_id}"
    session = await get_session()
    try:
        async with session.delete(url, headers=HEADERS) as response:
            return response.status in (200, 204)
    except Exception as e:
        logger.error(f"[DB] Error in clear_history: {e}")
        return False

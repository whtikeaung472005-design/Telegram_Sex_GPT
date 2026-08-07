# Filename: db_manager.py
import os
import time
import aiohttp
from typing import Dict, Any, Optional
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
FREE_RESET_SECONDS = 8 * 3600  # 8 Hours
PRO_RESET_SECONDS = 3 * 3600   # 3 Hours

FREE_MSG_LIMIT = 30
FREE_OUT_LIMIT = 1000

PRO_MSG_LIMIT = 100
PRO_OUT_LIMIT = 8000

async def get_or_create_user(telegram_id: int) -> Dict[str, Any]:
    """
    User ကို Database ထဲကနေ ရှာမယ်။ မရှိရင် အသစ် (Free Plan) နဲ့ ဖန်တီးမယ်။
    """
    url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return await _check_and_reset_limits(data[0])
            
            # User doesn't exist, create new
            current_time = int(time.time())
            new_user = {
                "telegram_id": telegram_id,
                "plan_type": "free",
                "message_count": 0,
                "token_count": 0,
                "last_reset": current_time
            }
            
            async with session.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json=new_user) as post_response:
                if post_response.status in (200, 201):
                    result = await post_response.json()
                    return result[0]
                else:
                    raise Exception(f"Failed to create user: {await post_response.text()}")

async def _check_and_reset_limits(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    အချိန်စေ့သွားရင် Limit တွေကို 0 ပြန်ထားပေးမယ့် (Auto-reset) လုပ်ဆောင်ချက်
    """
    current_time = int(time.time())
    last_reset = user_data.get("last_reset", 0)
    plan_type = user_data.get("plan_type", "free")
    
    reset_duration = PRO_RESET_SECONDS if plan_type == "pro" else FREE_RESET_SECONDS
    
    if (current_time - last_reset) >= reset_duration:
        # Reset is needed
        update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_data['telegram_id']}"
        update_data = {
            "message_count": 0,
            "token_count": 0,
            "last_reset": current_time
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(update_url, headers=HEADERS, json=update_data) as response:
                if response.status == 200:
                    updated_data = await response.json()
                    return updated_data[0]
    
    return user_data

async def check_usage_allowed(telegram_id: int) -> tuple[bool, str]:
    """
    User ဟာ ဆက်သုံးခွင့်ရှိ/မရှိ စစ်ဆေးပေးမယ့် Function
    """
    user = await get_or_create_user(telegram_id)
    plan = user["plan_type"]
    msg_count = user["message_count"]
    token_count = user["token_count"]
    
    msg_limit = PRO_MSG_LIMIT if plan == "pro" else FREE_MSG_LIMIT
    token_limit = PRO_OUT_LIMIT if plan == "pro" else FREE_OUT_LIMIT
    
    if msg_count >= msg_limit:
        return False, "MESSAGE_LIMIT_REACHED"
    
    if token_count >= token_limit:
        return False, "TOKEN_LIMIT_REACHED"
        
    return True, "ALLOWED"

async def update_usage(telegram_id: int, output_length: int) -> None:
    """
    AI ပြန်ဖြေပြီးတိုင်း အသုံးပြုမှု အရေအတွက်ကို တိုးပေးမယ့် Function
    """
    user = await get_or_create_user(telegram_id)
    
    update_url = f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{telegram_id}"
    update_data = {
        "message_count": user["message_count"] + 1,
        "token_count": user["token_count"] + output_length
    }
    
    async with aiohttp.ClientSession() as session:
        await session.patch(update_url, headers=HEADERS, json=update_data)
# Filename: ai_service.py
import os
import aiohttp
import logging
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = "google/gemma-4-31b-it"

SYSTEM_PROMPT = """[မင်းရဲ့ မူလ System Prompt အရှည်ကြီးကို ဒီနေရာမှာ အကုန်ထည့်ပါ]"""

# Global session object to prevent memory leaks and speed up requests
session: Optional[aiohttp.ClientSession] = None

async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session

async def generate_response(prompt: str, history: List[Dict[str, str]] = None) -> Optional[str]:
    """OpenRouter API သို့ Request ပို့ခြင်း"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/EducationAIBot", 
        "X-Title": "Education AI Telegram Bot"
    }
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.9, # ပိုပြီး ပီပြင်တဲ့ Roleplay ဖြစ်စေရန်
        "top_p": 0.9
    }

    try:
        s = await get_session()
        async with s.post(url, headers=headers, json=payload, timeout=60) as response:
            if response.status == 200:
                data = await response.json()
                return data['choices'][0]['message']['content']
            else:
                error_text = await response.text()
                logger.error(f"[AI Service Error] Status: {response.status}, Detail: {error_text}")
                return None
    except Exception as e:
        logger.error(f"[AI Service Exception] {str(e)}")
        return None

# Filename: ai_service.py
import os
import aiohttp
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = "google/gemma-4-26b-a4b-it"

async def generate_response(prompt: str) -> Optional[str]:
    """
    OpenRouter (Gemma Model) သို့ Asynchronous Request ပို့မယ့် Function.
    Error Handling အပြည့်အစုံ ပါဝင်ပါတယ်။
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/EducationAIBot", # Optional but recommended by OpenRouter
        "X-Title": "Education AI Telegram Bot"
    }
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a helpful and expert educational AI assistant. Answer clearly and concisely."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    print(f"[AI Service Error] Status: {response.status}, Detail: {error_text}")
                    return None
    except Exception as e:
        print(f"[AI Service Exception] {str(e)}")
        return None
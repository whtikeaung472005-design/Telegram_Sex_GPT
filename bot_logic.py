# Filename: bot_logic.py
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from dotenv import load_dotenv

from db_manager import check_usage_allowed, update_usage, get_or_create_user, save_chat, get_chat_history, clear_history
from ai_service import generate_response

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_upgrade_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Pro Plan ဝယ်ယူရန်", callback_data="buy_pro")]
    ])

WELCOME_GIF_URL = "https://srtteanzawxfaadaoelk.supabase.co/storage/v1/object/public/Telegram%20Ai%20photo/sexgpt.gif"

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await get_or_create_user(user_id)
    
    welcome_text = (
        f"မင်္ဂလာပါ {message.from_user.first_name}!\n\n"
        "သင့်ရဲ့ အလိုရမ္မက်တွေကို ဖြည့်ဆီးပေးဖို့ ကျွန်မ Sex GPT က သင့်အနားရှိနေပါပြီ။\n\n"
        "တူတူ မှောင်ဖို့အတွက် အဆင့်သင့်ဖြစ်နေပါပြီ။\n"
        "သင့်ရဲ့ မေးခွန်းတွေကို ယခုပဲ စတင်မေးမြန်းနိုင်ပါပြီ!"
    )
    try:
        await message.answer_animation(animation=WELCOME_GIF_URL, caption=welcome_text)
    except Exception as e:
        await message.answer(welcome_text)

async def setup_bot_commands(bot: Bot):
    bot_commands = [
        BotCommand(command="/new_chat", description="🔄 New Chat စတင်ရန်"),
        BotCommand(command="/admin", description="👨‍💻 Admin နှင့် ဆက်သွယ်ရန်"),
        BotCommand(command="/status", description="📊 အသုံးပြုမှု စစ်ဆေးရန်")
    ]
    await bot.set_my_commands(bot_commands)

@dp.message(Command("new_chat"))
async def cmd_new_chat(message: types.Message):
    user_id = message.from_user.id
    if await clear_history(user_id):
        await message.answer("✅ မှတ်ဉာဏ်ဟောင်းများကို အောင်မြင်စွာ ဖျက်လင်းလိုက်ပါပြီ။")
    else:
        await message.answer("⚠️ အမှားတစ်ခု ဖြစ်ပွားခဲ့ပါသည်။")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    await message.answer("👨‍💻 Admin နှင့် ဆက်သွယ်ရန် 👉 @slipme_mm")

@dp.message(F.text)
async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    
    is_allowed, reason, char_limit = await check_usage_allowed(user_id)
    if not is_allowed:
        return await message.answer("⚠️ သင်၏ Limit ပြည့်သွားပါပြီ။ Pro Plan သို့ ပြောင်းလဲပါ။", reply_markup=get_upgrade_keyboard())

    processing_msg = await message.answer("⏳ စဉ်းစားနေပါတယ်... ခဏလေးစောင့်ပေးပါ။")

    try:
        chat_history = await get_chat_history(user_id, limit=10)
        ai_response = await generate_response(user_text, history=chat_history)
        
        if not ai_response:
            return await processing_msg.edit_text("❌ AI စနစ် ချို့ယွင်းနေပါသည်။")
            
        if len(ai_response) > char_limit:
            ai_response = ai_response[:char_limit] + f"\n\n[⚠️ Plan ကန့်သတ်ချက် ({char_limit}) ပြည့်သွားပါသည်။]"
            
        await update_usage(user_id, len(ai_response))
        await save_chat(user_id, "user", user_text)
        await save_chat(user_id, "assistant", ai_response)
        
        await processing_msg.delete() 
        
        if len(ai_response) > 4096:
            for x in range(0, len(ai_response), 4096):
                await message.answer(ai_response[x:x+4096])
        else:
            await message.answer(ai_response)
            
    except Exception as e:
        logger.error(f"[Bot Logic Error] {e}")
        await processing_msg.edit_text("❌ အမှားအယွင်းတစ်ခု ဖြစ်ပွားခဲ့ပါသည်။")

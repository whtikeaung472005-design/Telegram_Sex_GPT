# Filename: bot_logic.py
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
from aiogram.types import BotCommand

# Import our custom modules
from db_manager import check_usage_allowed, update_usage, get_or_create_user, save_chat, get_chat_history, clear_history
from ai_service import generate_response

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Keyboards ---
def get_upgrade_keyboard() -> InlineKeyboardMarkup:
    """Pro Plan ဝယ်ယူရန်အတွက် Inline Keyboard ဖန်တီးခြင်း"""
    keyboard = [
        [InlineKeyboardButton(text="💎 Pro Plan ဝယ်ယူရန်", callback_data="buy_pro")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- Handlers ---
WELCOME_GIF_URL = "https://srtteanzawxfaadaoelk.supabase.co/storage/v1/object/public/Telegram%20Ai%20photo/sexgpt.gif"

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """User မှ /start နှိပ်သည့်အခါ အလုပ်လုပ်မည့် Function"""
    user_id = message.from_user.id
    await get_or_create_user(user_id) # Register user in DB
    
    welcome_text = (
        f"မင်္ဂလာပါ {message.from_user.first_name}!\n\n"
        "သင့်ရဲ့ အလိုရမ္မက်တွေကို ဖြည့်ဆီးပေးဖို့ ကျွန်မ Sex GPT က သင့်အနားရှိနေပါပြီ။\n\n"
        "တူတူ မှောင်ဖို့အတွက် အဆင့်သင့်ဖြစ်နေပါပြီ။\n"
        "သင့်ရဲ့ မေးခွန်းတွေကို ယခုပဲ စတင်မေးမြန်းနိုင်ပါပြီ!"
    )
    if WELCOME_GIF_URL:
        # GIF အတွက် answer_animation ကို အသုံးပြုခြင်း
        await message.answer_animation(animation=WELCOME_GIF_URL, caption=welcome_text)
    else:
        await message.answer(welcome_text) # အရန်အဖြစ် (Fallback)
        
async def setup_bot_commands(bot: Bot):
    """Telegram ဘယ်ဘက်အောက်ထောင့်ရှိ Menu Bar ကို တည်ဆောက်ခြင်း"""
    bot_commands = [
        BotCommand(command="/new_chat", description="🔄 New Chat စတင်ရန်"),
        BotCommand(command="/admin", description="👨‍💻 Admin နှင့် ဆက်သွယ်ရန်"),
        BotCommand(command="/status", description="📊 အသုံးပြုမှု စစ်ဆေးရန်")
    ]
    await bot.set_my_commands(bot_commands)

# --- Commands ---
@dp.message(Command("new_chat"))
async def cmd_new_chat(message: types.Message):
    """Conversation History အား ဖျက်ပစ်ပြီး အသစ်ပြန်စရန်"""
    user_id = message.from_user.id
    success = await clear_history(user_id)
    if success:
        await message.answer("✅ မှတ်ဉာဏ်ဟောင်းများကို အောင်မြင်စွာ ဖျက်လင်းလိုက်ပါပြီ။ အကြောင်းအရာ အသစ်များကို စတင် ဆွေးနွေးနိုင်ပါပြီ။")
    else:
        await message.answer("⚠️ မှတ်ဉာဏ်များ ဖျက်ရာတွင် အနည်းငယ် အမှားအယွင်းရှိပါသည်။ ပြန်လည်ကြိုးစားကြည့်ပါ။")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Admin သို့ ဆက်သွယ်ရန် လင့်ခ်ပေးခြင်း"""
    await message.answer("👨‍💻 Admin နှင့် ဆက်သွယ်ရန် လိုအပ်ပါက အောက်ပါ လင့်ခ်မှတစ်ဆင့် ဆက်သွယ်နိုင်ပါသည်:\n\n👉 @slipme_mm")

# (cmd_start နှင့် cmd_status များကို မူလအတိုင်းထားပါ)

@dp.message(F.text)
async def handle_user_message(message: types.Message):
    """User ထံမှ ဝင်လာသော စာများကို လက်ခံပြီး AI ထံ ပို့ပေးခြင်း (History နှင့်တကွ)"""
    user_id = message.from_user.id
    user_text = message.text
    
    is_allowed, reason, char_limit = await check_usage_allowed(user_id)
    
    if not is_allowed:
        limit_msg = "⚠️ သင်၏ မေးခွန်းအရေအတွက် (Limit) ပြည့်သွားပါပြီ။ သတ်မှတ်ချိန်ပြည့်ရန် စောင့်ပါ သို့မဟုတ် Pro Plan သို့ ပြောင်းလဲပါ။"
        # get_upgrade_keyboard() ကို အသုံးပြုရန်
        return await message.answer(limit_msg)

    processing_msg = await message.answer("⏳ စဉ်းစားနေပါတယ်... ခဏလေးစောင့်ပေးပါ။")

    try:
        # DB မှ History များကို ဆွဲထုတ်ခြင်း (အများဆုံး ၁၀ ကြိမ်)
        chat_history = await get_chat_history(user_id, limit=10)
        
        # AI ဆီသို့ History တွဲလျက် Request ပို့ခြင်း
        ai_response = await generate_response(user_text, history=chat_history)
        
        if not ai_response:
            return await processing_msg.edit_text("❌ တောင်းပန်ပါတယ်။ ယခုအချိန်တွင် AI စနစ် ချို့ယွင်းနေပါသည်။ ခဏအကြာမှ ထပ်မံကြိုးစားကြည့်ပါ။")
            
        if len(ai_response) > char_limit:
            ai_response = ai_response[:char_limit] + f"\n\n[⚠️ သင့် Plan ၏ တစ်ကြိမ်စာ စာလုံးရေ ကန့်သတ်ချက် ({char_limit}) ပြည့်သွားပါသဖြင့် အဖြေကို ရပ်တန့်လိုက်ပါသည်။]"
            
        output_length = len(ai_response)
        await update_usage(user_id, output_length)
        
        # 📌 အောင်မြင်ပါက User Prompt နှင့် AI Response ကို DB တွင် သိမ်းဆည်းခြင်း
        await save_chat(user_id, "user", user_text)
        await save_chat(user_id, "assistant", ai_response)
        
        await processing_msg.delete() 
        
        if len(ai_response) > 4096:
            for x in range(0, len(ai_response), 4096):
                await message.answer(ai_response[x:x+4096])
        else:
            await message.answer(ai_response)
            
    except Exception as e:
        print(f"[Bot Logic Error] {e}")
        await processing_msg.edit_text("❌ အမှားအယွင်းတစ်ခု ဖြစ်ပွားခဲ့ပါသည်။")

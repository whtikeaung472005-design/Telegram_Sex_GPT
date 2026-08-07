# Filename: bot_logic.py
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv

# Import our custom modules
from db_manager import check_usage_allowed, update_usage, get_or_create_user
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
WELCOME_GIF_URL = os.getenv("https://srtteanzawxfaadaoelk.supabase.co/storage/v1/object/public/Telegram%20Ai%20photo/sexgpt.gif")

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

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """User ၏ လက်ရှိ အသုံးပြုမှု အခြေအနေကို စစ်ဆေးရန်"""
    user_id = message.from_user.id
    user_data = await get_or_create_user(user_id)
    
    plan_type = "💎 Pro Plan" if user_data["plan_type"] == "pro" else "🆓 Free Plan"
    msg_limit = 100 if user_data["plan_type"] == "pro" else 20
    char_limit = 8000 if user_data["plan_type"] == "pro" else 1000
    reset_hours = 4 if user_data["plan_type"] == "pro" else 8
    
    status_text = (
        f"📊 **သင့်ရဲ့ အသုံးပြုမှု အခြေအနေ**\n\n"
        f"Plan: {plan_type}\n"
        f"Messages Used: {user_data['message_count']} / {msg_limit}\n"
        f"Reset Time: မေးခွန်းပြည့်သွားပါက {reset_hours} နာရီ စောင့်ရပါမည်။\n"
        f"Max Length: တစ်ခါဖြေလျှင် စာလုံးရေ {char_limit} အထိ ရရှိမည်။\n"
    )
    
    if user_data["plan_type"] == "free":
        await message.answer(status_text, reply_markup=get_upgrade_keyboard())
    else:
        await message.answer(status_text)

@dp.message(F.text)
async def handle_user_message(message: types.Message):
    """User ထံမှ ဝင်လာသော စာများကို လက်ခံပြီး AI ထံ ပို့ပေးခြင်း"""
    user_id = message.from_user.id
    user_text = message.text
    
    # 1. Check Usage Limits 
    is_allowed, reason, char_limit = await check_usage_allowed(user_id)
    
    if not is_allowed:
        limit_msg = "⚠️ သင်၏ မေးခွန်းအရေအတွက် (Limit) ပြည့်သွားပါပြီ။ သတ်မှတ်ချိန်ပြည့်ရန် စောင့်ပါ သို့မဟုတ် Pro Plan သို့ ပြောင်းလဲပါ။"
        await message.answer(limit_msg, reply_markup=get_upgrade_keyboard())
        return

    # 2. Send "Loading" Message (Typing အစား ယာယီ Message ပို့ခြင်း - Bulletproof UX)
    processing_msg = await message.answer("⏳ SEX GPT စဉ်းစားနေပါတယ်... ခဏလေးစောင့်ပေးပါ။")

    try:
        # 3. Get AI Response
        ai_response = await generate_response(user_text)
        
        if not ai_response:
            # ယာယီ Message ကို Error Message ဖြင့် အစားထိုးခြင်း
            await processing_msg.edit_text("❌ တောင်းပန်ပါတယ်။ ယခုအချိန်တွင် AI စနစ် ချို့ယွင်းနေပါသည်။ ခဏအကြာမှ ထပ်မံကြိုးစားကြည့်ပါ။")
            return
            
        # 4. Truncate Response if it exceeds the limit
        if len(ai_response) > char_limit:
            ai_response = ai_response[:char_limit] + f"\n\n[⚠️ သင့် Plan ၏ တစ်ကြိမ်စာ စာလုံးရေ ကန့်သတ်ချက် ({char_limit}) ပြည့်သွားပါသဖြင့် အဖြေကို ရပ်တန့်လိုက်ပါသည်။]"
            
        # 5. Calculate output length & Update DB 
        output_length = len(ai_response)
        await update_usage(user_id, output_length)
        
        # 6. Delete Loading Message and Send Final Response
        await processing_msg.delete() 
        
        if len(ai_response) > 4096:
            for x in range(0, len(ai_response), 4096):
                await message.answer(ai_response[x:x+4096])
        else:
            await message.answer(ai_response)
            
    except Exception as e:
        print(f"[Bot Logic Error] {e}")
        # Processing message ကို error message အဖြစ် ပြောင်းလဲဖော်ပြခြင်း
        await processing_msg.edit_text("❌ အမှားအယွင်းတစ်ခု ဖြစ်ပွားခဲ့ပါသည်။")

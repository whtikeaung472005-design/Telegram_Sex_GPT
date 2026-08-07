# Filename: bot_logic.py
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
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
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """User မှ /start နှိပ်သည့်အခါ အလုပ်လုပ်မည့် Function"""
    user_id = message.from_user.id
    await get_or_create_user(user_id) # Register user in DB
    
    welcome_text = (
        f"မင်္ဂလာပါ {message.from_user.first_name}!\n\n"
        "ကျွန်တော်ကတော့ ပညာရေးနဲ့ ပတ်သက်ပြီး သင်သိချင်တာတွေကို ဖြေကြားပေးမယ့် AI Agent Bot ဖြစ်ပါတယ်။\n\n"
        "✨ Free Plan အနေနဲ့ ၈ နာရီအတွင်း မေးခွန်း (၃၀) ခု နှင့် စာလုံးရေ (၁၀၀၀) အထိ မေးမြန်းနိုင်ပါတယ်။\n\n"
        "သင့်ရဲ့ မေးခွန်းတွေကို ယခုပဲ စတင်မေးမြန်းနိုင်ပါပြီ!"
    )
    await message.answer(welcome_text)

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """User ၏ လက်ရှိ အသုံးပြုမှု အခြေအနေကို စစ်ဆေးရန်"""
    user_id = message.from_user.id
    user_data = await get_or_create_user(user_id)
    
    plan_type = "💎 Pro Plan" if user_data["plan_type"] == "pro" else "🆓 Free Plan"
    msg_limit = 100 if user_data["plan_type"] == "pro" else 30
    token_limit = 8000 if user_data["plan_type"] == "pro" else 1000
    
    status_text = (
        f"📊 **သင့်ရဲ့ အသုံးပြုမှု အခြေအနေ**\n\n"
        f"Plan: {plan_type}\n"
        f"Messages Used: {user_data['message_count']} / {msg_limit}\n"
        f"Characters Used: {user_data['token_count']} / {token_limit}\n"
    )
    
    if user_data["plan_type"] == "free":
        await message.answer(status_text, reply_markup=get_upgrade_keyboard())
    else:
        await message.answer(status_text)

@dp.callback_query(F.data == "buy_pro")
async def process_buy_pro(callback: CallbackQuery):
    """User မှ 'Pro ဝယ်ယူရန်' ခလုတ်ကို နှိပ်သည့်အခါ"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "No Username"
    
    # Notify User
    await callback.message.answer(
        "🙏 စိတ်ဝင်စားတဲ့အတွက် ကျေးဇူးတင်ပါတယ်။ သင့်ရဲ့ အချက်အလက်ကို Admin ထံ ပေးပို့လိုက်ပါပြီ။\n"
        "Admin မှ သင့်အား မကြာမီ ဆက်သွယ်ပေးပါလိမ့်မည်။"
    )
    await callback.answer()
    
    # Notify Admin
    if ADMIN_ID:
        admin_alert = (
            f"💰 **New Pro Plan Request!**\n\n"
            f"User ID: `{user_id}`\n"
            f"Username: @{username}\n\n"
            f"Database ထဲတွင် အထက်ပါ User ID အား plan_type 'pro' ဟု ပြောင်းပေးပါ။"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown")
        except Exception as e:
            print(f"[Admin Alert Error] Failed to send alert to admin: {e}")

@dp.message(F.text)
async def handle_user_message(message: types.Message):
    """User ထံမှ ဝင်လာသော စာများကို လက်ခံပြီး AI ထံ ပို့ပေးခြင်း"""
    user_id = message.from_user.id
    user_text = message.text
    
    # 1. Check Usage Limits
    is_allowed, reason = await check_usage_allowed(user_id)
    
    if not is_allowed:
        if reason == "MESSAGE_LIMIT_REACHED":
            limit_msg = "⚠️ သင်၏ အခမဲ့ မေးခွန်းအရေအတွက် (Limit) ပြည့်သွားပါပြီ။ အချိန်ပြည့်ရန် စောင့်ပါ သို့မဟုတ် Pro Plan သို့ ပြောင်းလဲပါ။"
        else:
            limit_msg = "⚠️ သင်၏ အခမဲ့ စာလုံးရေ (Character Limit) ပြည့်သွားပါပြီ။ အချိန်ပြည့်ရန် စောင့်ပါ သို့မဟုတ် Pro Plan သို့ ပြောင်းလဲပါ။"
            
        await message.answer(limit_msg, reply_markup=get_upgrade_keyboard())
        return

    # 2. Show "Typing..." action to user while AI is thinking
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        # 3. Get AI Response
        ai_response = await generate_response(user_text)
        
        if not ai_response:
            await message.answer("❌ တောင်းပန်ပါတယ်။ ယခုအချိန်တွင် AI စနစ် ချို့ယွင်းနေပါသည်။ ခဏအကြာမှ ထပ်မံကြိုးစားကြည့်ပါ။")
            return
            
        # 4. Calculate output length & Update DB
        output_length = len(ai_response)
        await update_usage(user_id, output_length)
        
        # 5. Send response back to user
        # Safe sending: Very long AI responses (over 4096 chars) need to be chunked in Telegram
        if len(ai_response) > 4096:
            for x in range(0, len(ai_response), 4096):
                await message.answer(ai_response[x:x+4096])
        else:
            await message.answer(ai_response)
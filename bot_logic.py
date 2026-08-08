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

ADMIN_ID = os.getenv("ADMIN_ID")

@dp.message(Command("givepro"))
async def cmd_give_pro(message: types.Message):
    """Admin မှ User တစ်ဦးကို Pro ပေးရန်: /givepro 12345678"""
    # Admin ဟုတ်မဟုတ် အရင်စစ်မယ်
    if str(message.from_user.id) != ADMIN_ID:
        return await message.answer("❌ သင်သည် ဤ Command ကို အသုံးပြုခွင့်မရှိပါ။")

    # Command ရဲ့ နောက်မှာ user_id ပါမပါ စစ်မယ်
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("⚠️ အသုံးပြုပုံ မှားယွင်းနေပါသည်။\nဥပမာ- `/givepro 12345678`", parse_mode="Markdown")

    target_user_id = args[1]
    
    # Database မှာ Plan ကို Pro ပြောင်းမယ်
    success = await set_user_plan(int(target_user_id), "pro")
    
    if success:
        await message.answer(f"✅ User `{target_user_id}` ကို Pro Plan ပေးပြီးပါပြီ။", parse_mode="Markdown")
        # User ကိုလည်း အကြောင်းကြားပေးမယ်
        try:
            await bot.send_message(target_user_id, "🎉 ဂုဏ်ယူပါတယ်! သင့်ကို Pro Plan အဆင့်မြှင့်ပေးလိုက်ပါပြီ။ အခုပဲ အကန့်အသတ်မရှိ အသုံးပြုနိုင်ပါပြီ။")
        except Exception:
            pass # User က Bot ကို block ထားရင် error တက်မှာမို့လို့ ignore လုပ်ထားတာ
    else:
        await message.answer("❌ အမှားတစ်ခု ဖြစ်ပွားခဲ့ပါသည်။ User ID မှန်မမှန် ပြန်စစ်ပါ။")

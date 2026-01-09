from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()

# Resumelarni sessiyada saqlash
employer_resumes = {}

def get_candidate_keyboard(current_index: int, total: int) -> InlineKeyboardMarkup:
    """Nomzodlar uchun navigatsiya klaviaturasi"""
    buttons = []
    
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"can_prev_{current_index}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"📊 {current_index + 1}/{total}", callback_data="can_count"))
    
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"can_next_{current_index}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="close_candidates")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_resume_message(resume: dict) -> str:
    """Rezyumeni xabar formatiga o'tkazish"""
    return f"""
👨‍💼 <b>NOMZOD: {resume.get('full_name')}</b> ({resume.get('age')} yosh)

💼 <b>Sohasi:</b> {resume.get('profession')}
💻 <b>Stack:</b> {resume.get('technology')}
💰 <b>Kutilayotgan maosh:</b> {resume.get('salary')}
📍 <b>Hudud:</b> {resume.get('region')}

📞 <b>Tel:</b> {resume.get('phone')}
✈️ <b>Telegram:</b> {resume.get('telegram_username')}
⏰ <b>Aloqa vaqti:</b> {resume.get('call_time')}

🎯 <b>Maqsad:</b>
{resume.get('goal')}
"""


async def show_candidates(message: Message, user_id: int = None):
    """Nomzodlarni ko'rsatish"""
    if user_id is None:
        user_id = message.from_user.id
    
    # Role check + Admin check
    user_data = await db.get_user(user_id)
    from config import ADMIN_IDS
    
    is_admin = user_id in ADMIN_IDS
    if not is_admin and (not user_data or user_data.get('role') != 'employer'):
        await message.answer("❌ Bu bo'lim faqat Ish beruvchilar uchun.")
        return

    resumes = await db.get_resumes(limit=100)
    
    if not resumes:
        await message.answer("😕 Hozircha hech qanday nomzod topilmadi.")
        return

    employer_resumes[user_id] = {
        'resumes': resumes,
        'current_index': 0
    }
    
    await send_candidate_to_employer(message, user_id, 0)

async def send_candidate_to_employer(message_or_callback, user_id: int, index: int):
    """Rezyumeni yuborish yoki yangilash"""
    if user_id not in employer_resumes:
        return
    
    data = employer_resumes[user_id]
    resumes = data['resumes']
    vacancy = resumes[index]
    data['current_index'] = index
    
    text = format_resume_message(vacancy)
    keyboard = get_candidate_keyboard(index, len(resumes))
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode='HTML')

@router.callback_query(F.data.startswith("can_next_"))
async def next_candidate(callback: CallbackQuery):
    current_index = int(callback.data.split("_")[2])
    await send_candidate_to_employer(callback, callback.from_user.id, current_index + 1)

@router.callback_query(F.data.startswith("can_prev_"))
async def prev_candidate(callback: CallbackQuery):
    current_index = int(callback.data.split("_")[2])
    await send_candidate_to_employer(callback, callback.from_user.id, current_index - 1)

@router.callback_query(F.data == "close_candidates")
async def close_candidates(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = Router()


# FSM States
class PostVacancyStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_company = State()
    waiting_for_description = State()
    waiting_for_salary_min = State()
    waiting_for_salary_max = State()
    waiting_for_location = State()
    waiting_for_experience = State()
    waiting_for_contact = State()
    confirming = State()


def get_experience_keyboard():
    """Tajriba darajasi klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Tajribasiz", callback_data="post_exp_no_experience")],
            [InlineKeyboardButton(text="🟡 1-3 yil", callback_data="post_exp_between_1_and_3")],
            [InlineKeyboardButton(text="🟠 3-6 yil", callback_data="post_exp_between_3_and_6")],
            [InlineKeyboardButton(text="🔴 6+ yil", callback_data="post_exp_more_than_6")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post_vacancy")]
        ]
    )


def get_confirm_keyboard():
    """Tasdiqlash klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ E'lon qilish", callback_data="confirm_post_vacancy"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit_post_vacancy")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post_vacancy")
            ]
        ]
    )


@router.message(F.text == "📢 Vakansiya qo'shish")
async def start_post_vacancy(message: Message, state: FSMContext):
    """Vakansiya qo'shishni boshlash"""
    # Premium tekshirish
    is_premium = await db.is_premium(message.from_user.id)
    
    if not is_premium:
        await message.answer(
            "🔒 <b>Premium xususiyat!</b>\n\n"
            "Vakansiya qo'shish faqat Premium foydalanuvchilar uchun mavjud.\n\n"
            "💎 Premium obuna bilan:\n"
            "• Vakansiya e'lon qilish\n"
            "• Cheksiz qidiruvlar\n"
            "• Telegram kanallaridan qidirish\n"
            "• Avtomatik bildirishnomalar\n\n"
            "Premium sotib olish uchun 💎 Premium bo'limiga o'ting.",
            parse_mode='HTML'
        )
        return
    
    await message.answer(
        "📢 <b>Vakansiya e'lon qilish</b>\n\n"
        "Yangi vakansiyani botga joylang va u barcha foydalanuvchilarga ko'rsatiladi!\n\n"
        "Keling, boshlaylik. Vakansiya nomini kiriting:\n\n"
        "<b>Misol:</b> <code>Python Backend Developer</code>\n\n"
        "Yoki /cancel bekor qilish uchun",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_title)


@router.message(PostVacancyStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Vakansiya nomini qabul qilish"""
    title = message.text.strip()
    
    if len(title) < 5:
        await message.answer("❌ Vakansiya nomi juda qisqa. Kamida 5 ta belgi kiriting.")
        return
    
    await state.update_data(title=title)
    
    await message.answer(
        f"✅ Vakansiya: <b>{title}</b>\n\n"
        f"Kompaniya nomini kiriting:\n\n"
        f"<b>Misol:</b> <code>Tashkent IT Park</code>",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_company)


@router.message(PostVacancyStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Kompaniya nomini qabul qilish"""
    company = message.text.strip()
    
    if len(company) < 2:
        await message.answer("❌ Kompaniya nomi juda qisqa.")
        return
    
    await state.update_data(company=company)
    
    await message.answer(
        f"✅ Kompaniya: <b>{company}</b>\n\n"
        f"Vakansiya tavsifini kiriting:\n\n"
        f"<b>Misol:</b>\n"
        f"<code>Bizga Python Backend Developer kerak.\n"
        f"Talablar:\n"
        f"- Python, Django\n"
        f"- PostgreSQL\n"
        f"- REST API</code>",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_description)


@router.message(PostVacancyStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Tavsifni qabul qilish"""
    description = message.text.strip()
    
    if len(description) < 20:
        await message.answer("❌ Tavsif juda qisqa. Kamida 20 ta belgi kiriting.")
        return
    
    await state.update_data(description=description)
    
    await message.answer(
        "✅ Tavsif saqlandi\n\n"
        "Minimal maoshni kiriting (so'm):\n\n"
        "<b>Misol:</b> <code>5000000</code>\n\n"
        "Yoki /skip maosh ko'rsatmaslik uchun",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_salary_min)


@router.message(PostVacancyStates.waiting_for_salary_min)
async def process_salary_min(message: Message, state: FSMContext):
    """Minimal maoshni qabul qilish"""
    if message.text.strip() == "/skip":
        await state.update_data(salary_min=None)
    else:
        try:
            salary_min = int(message.text.strip().replace(' ', '').replace(',', ''))
            await state.update_data(salary_min=salary_min)
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
            return
    
    await message.answer(
        "Maksimal maoshni kiriting (so'm):\n\n"
        "<b>Misol:</b> <code>8000000</code>\n\n"
        "Yoki /skip",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_salary_max)


@router.message(PostVacancyStates.waiting_for_salary_max)
async def process_salary_max(message: Message, state: FSMContext):
    """Maksimal maoshni qabul qilish"""
    if message.text.strip() == "/skip":
        await state.update_data(salary_max=None)
    else:
        try:
            salary_max = int(message.text.strip().replace(' ', '').replace(',', ''))
            await state.update_data(salary_max=salary_max)
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
            return
    
    await message.answer(
        "Joylashuvni kiriting:\n\n"
        "<b>Misol:</b> <code>Tashkent</code>",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_location)


@router.message(PostVacancyStates.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    """Joylashuvni qabul qilish"""
    location = message.text.strip()
    
    if len(location) < 2:
        await message.answer("❌ Joylashuv nomi juda qisqa.")
        return
    
    await state.update_data(location=location)
    
    await message.answer(
        "✅ Joylashuv saqlandi\n\n"
        "Tajriba darajasini tanlang:",
        reply_markup=get_experience_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_experience)


@router.callback_query(F.data.startswith("post_exp_"))
async def process_experience(callback: CallbackQuery, state: FSMContext):
    """Tajriba darajasini qabul qilish"""
    experience = callback.data.replace("post_exp_", "")
    await state.update_data(experience_level=experience)
    
    await callback.message.edit_text(
        "✅ Tajriba saqlandi\n\n"
        "Bog'lanish ma'lumotlarini kiriting:\n\n"
        "<b>Misol:</b>\n"
        "<code>Telegram: @hr_manager\n"
        "Tel: +998901234567</code>",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_contact)
    await callback.answer()


@router.message(PostVacancyStates.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Bog'lanish ma'lumotlarini qabul qilish"""
    contact = message.text.strip()
    
    if len(contact) < 5:
        await message.answer("❌ Bog'lanish ma'lumoti juda qisqa.")
        return
    
    await state.update_data(contact=contact)
    
    # Ma'lumotlarni ko'rsatish
    data = await state.get_data()
    
    salary_min = data.get('salary_min')
    salary_max = data.get('salary_max')
    
    if salary_min and salary_max:
        salary_text = f"{salary_min:,} - {salary_max:,} so'm"
    elif salary_min:
        salary_text = f"dan {salary_min:,} so'm"
    elif salary_max:
        salary_text = f"gacha {salary_max:,} so'm"
    else:
        salary_text = "Ko'rsatilmagan"
    
    exp_map = {
        'no_experience': '🟢 Tajribasiz',
        'between_1_and_3': '🟡 1-3 yil',
        'between_3_and_6': '🟠 3-6 yil',
        'more_than_6': '🔴 6+ yil'
    }
    
    preview = f"""
📢 <b>VAKANSIYA E'LONI - TEKSHIRISH</b>

🔹 <b>{data['title']}</b>

🏢 <b>Kompaniya:</b> {data['company']}
💰 <b>Maosh:</b> {salary_text}
📍 <b>Joylashuv:</b> {data['location']}
👔 <b>Tajriba:</b> {exp_map.get(data['experience_level'], 'N/A')}

📝 <b>Tavsif:</b>
{data['description'][:300]}{'...' if len(data['description']) > 300 else ''}

📞 <b>Bog'lanish:</b>
{contact}

━━━━━━━━━━━━━━━━

Ma'lumotlar to'g'rimi?
"""
    
    await message.answer(
        preview,
        reply_markup=get_confirm_keyboard(),
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.confirming)


@router.callback_query(F.data == "confirm_post_vacancy")
async def confirm_post(callback: CallbackQuery, state: FSMContext):
    """Vakansiyani tasdiqlash va e'lon qilish"""
    data = await state.get_data()
    
    try:
        # Vakansiyani database'ga qo'shish
        now = datetime.now(timezone.utc)
        
        vacancy_id = f"user_{callback.from_user.id}_{int(now.timestamp())}"
        
        # Vakansiyani saqlash
        await db.add_vacancy(
            external_id=vacancy_id,
            title=data['title'],
            company=data['company'],
            description=data['description'] + f"\n\n📞 Bog'lanish: {data['contact']}",
            salary_min=data.get('salary_min'),
            salary_max=data.get('salary_max'),
            location=data['location'],
            experience_level=data['experience_level'],
            url=f"https://t.me/{callback.from_user.username or 'bot'}",
            source='user_post',
            published_date=now
        )
        
        await callback.message.edit_text(
            "✅✅✅ <b>VAKANSIYA E'LON QILINDI!</b>\n\n"
            "Vakansiyangiz barcha foydalanuvchilarga ko'rsatiladi.\n\n"
            "📊 E'lon statistikasi:\n"
            "• Qidiruv natijalarida ko'rsatiladi\n"
            "• Filtrlarga mos foydalanuvchilarga yuboriladi\n"
            "• 30 kun faol bo'ladi\n\n"
            "✨ Rahmat, Premium foydalanuvchi!",
            parse_mode='HTML'
        )
        
        # Barcha adminlarga xabar
        from config import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"📢 <b>Yangi vakansiya e'lon qilindi!</b>\n\n"
                    f"👤 Foydalanuvchi: {callback.from_user.first_name} (@{callback.from_user.username})\n"
                    f"💼 Vakansiya: {data['title']}\n"
                    f"🏢 Kompaniya: {data['company']}\n"
                    f"📍 Joylashuv: {data['location']}",
                    parse_mode='HTML'
                )
            except:
                pass
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Vakansiya e'lon qilishda xatolik: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring.",
            parse_mode='HTML'
        )
        await state.clear()
    
    await callback.answer()


@router.callback_query(F.data == "edit_post_vacancy")
async def edit_post(callback: CallbackQuery, state: FSMContext):
    """Vakansiyani qayta tahrirlash"""
    await callback.message.edit_text(
        "✏️ Qayta tahrirlash uchun /post komandasi bilan qaytadan boshlang.\n\n"
        "Yoki /cancel bekor qilish uchun",
        parse_mode='HTML'
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_post_vacancy")
async def cancel_post(callback: CallbackQuery, state: FSMContext):
    """Bekor qilish"""
    await callback.message.edit_text(
        "❌ Vakansiya e'lon qilish bekor qilindi.",
        parse_mode='HTML'
    )
    await state.clear()
    await callback.answer()


@router.message(F.text == "/cancel")
async def cancel_command(message: Message, state: FSMContext):
    """Cancel komandasi"""
    current_state = await state.get_state()
    
    if current_state and current_state.startswith('PostVacancyStates'):
        await message.answer("❌ Vakansiya e'lon qilish bekor qilindi.")
        await state.clear()
    else:
        await message.answer("Hozir hech narsa bekor qilinmaydi.")
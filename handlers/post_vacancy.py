
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = Router()

# FSM States for Vacancy (Employer)
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

# FSM States for Resume (Seeker)
class PostResumeStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_technology = State()
    waiting_for_telegram = State()
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_salary = State()
    waiting_for_profession = State()
    waiting_for_call_time = State()
    waiting_for_goal = State()
    confirming = State()

# --- Common Utilities ---

def get_experience_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Tajribasiz", callback_data="post_exp_no_experience")],
        [InlineKeyboardButton(text="🟡 1-3 yil", callback_data="post_exp_between_1_and_3")],
        [InlineKeyboardButton(text="🟠 3-6 yil", callback_data="post_exp_between_3_and_6")],
        [InlineKeyboardButton(text="🔴 6+ yil", callback_data="post_exp_more_than_6")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post")]
    ])

def get_confirm_keyboard(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ E'lon qilish", callback_data=f"confirm_{prefix}"),
            InlineKeyboardButton(text="✏️ O'zgartirish", callback_data=f"edit_{prefix}")
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post")]
    ])

def get_region_keyboard():
    regions = ["Toshkent", "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Xorazm", "Namangan", "Navoiy", "Qashqadaryo", "Samarqand", "Sirdaryo", "Surxondaryo", "Qoraqalpog'iston"]
    rows = []
    current_row = []
    for reg in regions:
        current_row.append(InlineKeyboardButton(text=reg, callback_data=f"region_{reg}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# --- Entry Points ---

@router.message(F.text == "📢 Vakansiya qo'shish")
async def start_add_content(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Ish beruvchi (Vakansiya qo'shish)", callback_data="start_employer_flow")],
        [InlineKeyboardButton(text="👨‍💼 Ish qidiruvchi (Rezyume qo'shish)", callback_data="start_seeker_flow")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_post")]
    ])
    await message.answer("📝 <b>Ma'lumot qo'shish</b>\n\nKim sifatida ma'lumot qoldirmoqchisiz?", reply_markup=keyboard, parse_mode='HTML')

@router.callback_query(F.data == "cancel_post")
async def cancel_post(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()

@router.message(F.text == "/cancel")
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")

# --- EMPLOYER FLOW ---

@router.callback_query(F.data == "start_employer_flow")
async def start_employer_flow(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await db.pool.execute("UPDATE users SET role = 'employer' WHERE user_id = $1", user_id)
    
    is_premium = await db.is_premium(user_id)
    if not is_premium:
        await callback.message.edit_text(
            "🔒 <b>Premium xususiyat!</b>\n\nVakansiya qo'shish faqat Premium 'Ish beruvchi'lar uchun mavjud.\n\nPremium sotib olish uchun 💎 Premium bo'limiga o'ting.",
            parse_mode='HTML'
        )
        return

    await callback.message.edit_text(
        "📢 <b>Vakansiya e'lon qilish</b>\n\n1. Kompaniya nomini kiriting:",
        parse_mode='HTML'
    )
    await state.set_state(PostVacancyStates.waiting_for_company)

@router.message(PostVacancyStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    await state.update_data(company=message.text)
    await message.answer("2. Vakansiya Nomi (Profession) ni kiriting:\nMisol: Python Developer")
    await state.set_state(PostVacancyStates.waiting_for_title)

@router.message(PostVacancyStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("3. Maoshni kiriting (Minimal):\nMisol: 5000000 (yoki 'Kelishilgan')")
    await state.set_state(PostVacancyStates.waiting_for_salary_min)

@router.message(PostVacancyStates.waiting_for_salary_min)
async def process_salary_min(message: Message, state: FSMContext):
    await state.update_data(salary_min=message.text)
    await message.answer("Maksimal maosh (ixtiyoriy, /skip):")
    await state.set_state(PostVacancyStates.waiting_for_salary_max)

@router.message(PostVacancyStates.waiting_for_salary_max)
async def process_salary_max(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(salary_max=message.text)
    await message.answer("4. Joylashuvni kiriting (Shahar/Viloyat):")
    await state.set_state(PostVacancyStates.waiting_for_location)

@router.message(PostVacancyStates.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.answer("5. Tajriba darajasini tanlang:", reply_markup=get_experience_keyboard())
    await state.set_state(PostVacancyStates.waiting_for_experience)

@router.callback_query(PostVacancyStates.waiting_for_experience)
async def process_experience(callback: CallbackQuery, state: FSMContext):
    exp = callback.data.replace("post_exp_", "")
    await state.update_data(experience=exp)
    await callback.message.edit_text("6. Aloqa uchun kontakt:\nMisol: +998901234567, @username")
    await state.set_state(PostVacancyStates.waiting_for_contact)

@router.message(PostVacancyStates.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer("7. Tavsif (Batafsil ma'lumot):")
    await state.set_state(PostVacancyStates.waiting_for_description)

@router.message(PostVacancyStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    
    preview = f"""📢 <b>VAKANSIYA TEKSHIRISH</b>
🏢 <b>{data.get('company')}</b>
💼 <b>{data.get('title')}</b>
💰 Maosh: {data.get('salary_min')} - {data.get('salary_max', '')}
📍 Joy: {data.get('location')}
📞 Aloqa: {data.get('contact')}
📝 Tavsif: {data.get('description')}
    """
    await message.answer(preview, reply_markup=get_confirm_keyboard("vacancy"), parse_mode='HTML')
    await state.set_state(PostVacancyStates.confirming)

@router.callback_query(F.data == "confirm_vacancy")
async def confirm_vacancy(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    now = datetime.now(timezone.utc)
    vacancy_id = f"user_{callback.from_user.id}_{int(now.timestamp())}"
    
    try:
        await db.add_vacancy(
            external_id=vacancy_id,
            title=data['title'],
            company=data['company'],
            description=f"{data['description']}\n\n📞 {data['contact']}",
            salary_min=int(data['salary_min']) if data['salary_min'].isdigit() else 0,
            location=data['location'],
            experience_level=data.get('experience', 'N/A'),
            url=f"https://t.me/{callback.from_user.username}",
            source='user_post',
            published_date=now
        )
        await callback.message.edit_text("✅ Vakansiya muvaffaqiyatli e'lon qilindi!")
        
        # --- MATCH ALERT - Ish qidiruvchilarga xabar berish ---
        try:
            from filters import vacancy_filter
            seekers = await db.get_all_seekers_with_filters()
            
            # Yangi vakansiya obyekti filtrlash uchun
            new_vacancy = {
                'title': data['title'],
                'company': data['company'],
                'description': data['description'],
                'salary_min': int(data['salary_min']) if data['salary_min'].isdigit() else 0,
                'salary_max': int(data['salary_max']) if data.get('salary_max', '').isdigit() else None,
                'location': data['location'],
                'experience_level': data.get('experience', 'N/A'),
                'source': 'user_post',
                'url': f"https://t.me/{callback.from_user.username or 'bot'}",
                'published_date': now
            }
            
            count = 0
            for seeker in seekers:
                # Seeker filtrlarini tayyorlash
                seeker_filter = {
                    'keywords': seeker.get('keywords', []),
                    'locations': seeker.get('locations', []),
                    'min_salary': seeker.get('salary_min'),
                    'max_salary': seeker.get('salary_max'),
                    'experience_level': seeker.get('experience_level')
                }
                
                # Mos kelishini tekshirish
                if vacancy_filter.apply_filters([new_vacancy], seeker_filter):
                    try:
                        alert_text = f"🔔 <b>Yangi mos vakansiya topildi!</b>\n\n"
                        alert_text += vacancy_filter.format_vacancy_message(new_vacancy)
                        
                        await callback.bot.send_message(
                            seeker['user_id'],
                            alert_text,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Alert yuborishda xatolik (user {seeker['user_id']}): {e}")
            
            logger.info(f"Match Alert: {count} ta foydalanuvchiga xabar yuborildi.")
        except Exception as e:
            logger.error(f"Match Alert jarayonida xatolik: {e}")

    except Exception as e:
        logger.error(f"Error posting vacancy: {e}")
        await callback.message.edit_text("❌ Xatolik yuz berdi.")
    await state.clear()

# --- SEEKER FLOW (RESUME) ---

@router.callback_query(F.data == "start_seeker_flow")
async def start_seeker_flow(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await db.pool.execute("UPDATE users SET role = 'seeker' WHERE user_id = $1", user_id)
    await callback.message.edit_text("👨‍💼 <b>Rezyume joylash</b>\n\n1. Ismingizni kiriting:", parse_mode='HTML')
    await state.set_state(PostResumeStates.waiting_for_name)

@router.message(PostResumeStates.waiting_for_name)
async def resume_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("2. Yoshingizni kiriting (raqamda):")
    await state.set_state(PostResumeStates.waiting_for_age)

@router.message(PostResumeStates.waiting_for_age)
async def resume_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    await state.update_data(age=int(message.text))
    await message.answer("3. Texnologiyalar (Stack):\nMisol: Python, Django, PostgreSQL")
    await state.set_state(PostResumeStates.waiting_for_technology)

@router.message(PostResumeStates.waiting_for_technology)
async def resume_tech(message: Message, state: FSMContext):
    await state.update_data(technology=message.text)
    await message.answer("4. Telegram username (@username):")
    await state.set_state(PostResumeStates.waiting_for_telegram)

@router.message(PostResumeStates.waiting_for_telegram)
async def resume_telegram(message: Message, state: FSMContext):
    await state.update_data(telegram_username=message.text)
    await message.answer("5. Aloqa uchun telefon raqam:")
    await state.set_state(PostResumeStates.waiting_for_phone)

@router.message(PostResumeStates.waiting_for_phone)
async def resume_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("6. Hududni tanlang:", reply_markup=get_region_keyboard())
    await state.set_state(PostResumeStates.waiting_for_region)

@router.callback_query(PostResumeStates.waiting_for_region)
async def resume_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.replace("region_", "")
    await state.update_data(region=region)
    await callback.message.edit_text(f"Tanlangan hudud: {region}\n\n7. Kutilayotgan maosh (Narxi):")
    await state.set_state(PostResumeStates.waiting_for_salary)

@router.message(PostResumeStates.waiting_for_salary)
async def resume_salary(message: Message, state: FSMContext):
    await state.update_data(salary=message.text)
    await message.answer("8. Kasbingiz (Title):\nMisol: Backend Developer")
    await state.set_state(PostResumeStates.waiting_for_profession)

@router.message(PostResumeStates.waiting_for_profession)
async def resume_profession(message: Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await message.answer("9. Murojaat qilish vaqti (Call time):\nMisol: 09:00 - 18:00")
    await state.set_state(PostResumeStates.waiting_for_call_time)

@router.message(PostResumeStates.waiting_for_call_time)
async def resume_call_time(message: Message, state: FSMContext):
    await state.update_data(call_time=message.text)
    await message.answer("10. Maqsad (Goal):\nQisqacha maqsadingiz:")
    await state.set_state(PostResumeStates.waiting_for_goal)

@router.message(PostResumeStates.waiting_for_goal)
async def resume_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    data = await state.get_data()
    
    preview = f"""👨‍💼 <b>REZYUME TEKSHIRISH</b>
👤 <b>{data.get('full_name')}</b> ({data.get('age')} yosh)
💻 Stack: {data.get('technology')}
💼 Kasb: {data.get('profession')}
💰 Maosh: {data.get('salary')}
📍 Hudud: {data.get('region')}
📞 Tel: {data.get('phone')}
✈️ Tg: {data.get('telegram_username')}
⏰ Vaqt: {data.get('call_time')}
🎯 Maqsad: {data.get('goal')}
    """
    await message.answer(preview, reply_markup=get_confirm_keyboard("resume"), parse_mode='HTML')
    await state.set_state(PostResumeStates.confirming)

@router.callback_query(F.data == "confirm_resume")
async def confirm_resume(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    try:
        await db.add_resume(
            user_id=callback.from_user.id,
            full_name=data['full_name'],
            age=data['age'],
            technology=data['technology'],
            telegram_username=data['telegram_username'],
            phone=data['phone'],
            region=data['region'],
            salary=data['salary'],
            profession=data['profession'],
            call_time=data['call_time'],
            goal=data['goal']
        )
        await callback.message.edit_text("✅ Rezyume muvaffaqiyatli joylandi!")
    except Exception as e:
        logger.error(f"Error adding resume: {e}")
        await callback.message.edit_text("❌ Xatolik yuz berdi.")
    await state.clear()
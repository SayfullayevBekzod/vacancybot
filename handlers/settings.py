from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
import logging

logger = logging.getLogger(__name__)

router = Router()


# FSM States
class SettingsStates(StatesGroup):
    waiting_for_keywords = State()
    waiting_for_locations = State()
    waiting_for_min_salary = State()
    waiting_for_max_salary = State()


def get_settings_keyboard(is_premium: bool = False):
    """Sozlamalar klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(text="🔑 Kalit so'zlar", callback_data="set_keywords"),
            InlineKeyboardButton(text="📍 Joylashuv", callback_data="set_locations")
        ],
        [
            InlineKeyboardButton(text="💰 Maosh", callback_data="set_salary"),
            InlineKeyboardButton(text="👔 Tajriba", callback_data="set_experience")
        ],
        [
            InlineKeyboardButton(text="🌐 Manbalar", callback_data="set_sources")
        ],
        [
            InlineKeyboardButton(text="📊 Joriy sozlamalar", callback_data="show_current_settings")
        ],
        [
            InlineKeyboardButton(text="📄 CV orqali sozlash (Auto)", callback_data="upload_cv_info")
        ],
        [
            InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_settings"),
            InlineKeyboardButton(text="❌ Yopish", callback_data="close_settings")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_experience_keyboard():
    """Tajriba darajasi klaviaturasi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Tajribasiz", callback_data="exp_no_experience")],
            [InlineKeyboardButton(text="🟡 1-3 yil", callback_data="exp_between_1_and_3")],
            [InlineKeyboardButton(text="🟠 3-6 yil", callback_data="exp_between_3_and_6")],
            [InlineKeyboardButton(text="🔴 6+ yil", callback_data="exp_more_than_6")],
            [InlineKeyboardButton(text="⚪️ Muhim emas", callback_data="exp_not_specified")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_settings")]
        ]
    )
    return keyboard


def get_sources_keyboard(is_premium: bool, current_sources: list = None):
    """Manbalar klaviaturasi"""
    current_sources = current_sources or ['hh_uz', 'user_post']
    
    buttons = []
    
    # hh.uz (hammaga)
    hh_selected = '✅' if 'hh_uz' in current_sources else '☐'
    buttons.append([
        InlineKeyboardButton(
            text=f"{hh_selected} 🌐 hh.uz",
            callback_data="toggle_source_hh_uz"
        )
    ])
    
    # User post (hammaga, avtomatik)
    buttons.append([
        InlineKeyboardButton(
            text="✅ 📢 Bot e'lonlar (avtomatik)",
            callback_data="info_user_post"
        )
    ])
    
    # Telegram (faqat Premium)
    if is_premium:
        tg_selected = '✅' if 'telegram' in current_sources else '☐'
        buttons.append([
            InlineKeyboardButton(
                text=f"{tg_selected} 📱 Telegram kanallar",
                callback_data="toggle_source_telegram"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="🔒 📱 Telegram (Premium)",
                callback_data="need_premium"
            )
        ])
    
    buttons.extend([
        [InlineKeyboardButton(text="💾 Saqlash", callback_data="save_sources")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_settings")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.text == "⚙️ Sozlamalar")
async def cmd_settings(message: Message):
    """Sozlamalar menyusi"""
    logger.info(f"Settings opened by user {message.from_user.id}")
    
    is_premium = await db.is_premium(message.from_user.id)
    
    text = """
⚙️ <b>Sozlamalar</b>

Sizga mos vakansiyalarni topish uchun quyidagi parametrlarni sozlang:

🔑 <b>Kalit so'zlar</b> - qidiruv so'zlari
📍 <b>Joylashuv</b> - shahar yoki viloyat
💰 <b>Maosh</b> - minimal va maksimal maosh
👔 <b>Tajriba</b> - tajriba darajasi
🌐 <b>Manbalar</b> - qayerdan qidirish (hh.uz, Telegram)

📊 Joriy sozlamalaringizni ko'rish uchun tugmani bosing.
"""
    
    await message.answer(
        text,
        reply_markup=get_settings_keyboard(is_premium),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Sozlamalarga qaytish"""
    await state.clear()
    
    is_premium = await db.is_premium(callback.from_user.id)
    
    text = """
⚙️ <b>Sozlamalar</b>

Sizga mos vakansiyalarni topish uchun quyidagi parametrlarni sozlang:

🔑 <b>Kalit so'zlar</b> - qidiruv so'zlari
📍 <b>Joylashuv</b> - shahar yoki viloyat
💰 <b>Maosh</b> - minimal va maksimal maosh
👔 <b>Tajriba</b> - tajriba darajasi
🌐 <b>Manbalar</b> - qayerdan qidirish
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(is_premium),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "show_current_settings")
async def show_current_settings(callback: CallbackQuery):
    """Joriy sozlamalarni ko'rsatish"""
    user_filter = await db.get_user_filter(callback.from_user.id)
    
    if not user_filter:
        text = "📊 <b>Joriy sozlamalar</b>\n\n⚠️ Hali sozlamalar o'rnatilmagan."
    else:
        keywords = user_filter.get('keywords', [])
        locations = user_filter.get('locations', [])
        salary_min = user_filter.get('salary_min')
        salary_max = user_filter.get('salary_max')
        experience = user_filter.get('experience_level')
        sources = user_filter.get('sources', ['hh_uz'])
        
        exp_map = {
            'no_experience': '🟢 Tajribasiz',
            'between_1_and_3': '🟡 1-3 yil',
            'between_3_and_6': '🟠 3-6 yil',
            'more_than_6': '🔴 6+ yil',
            'not_specified': '⚪️ Muhim emas'
        }
        
        # Manbalar matni
        sources_text = []
        if 'hh_uz' in sources:
            sources_text.append('🌐 hh.uz')
        if 'user_post' in sources:
            sources_text.append('📢 Bot e\'lonlar')
        if 'telegram' in sources:
            sources_text.append('📱 Telegram')
        
        text = f"""
📊 <b>Joriy sozlamalar</b>

🔑 <b>Kalit so'zlar:</b>
{', '.join(keywords) if keywords else '❌ Belgilanmagan'}

📍 <b>Joylashuv:</b>
{', '.join(locations) if locations else '❌ Barcha joylar'}

💰 <b>Maosh:</b>
{f"dan {salary_min:,} so'm" if salary_min else "❌"} - {f"gacha {salary_max:,} so'm" if salary_max else "cheksiz"}

👔 <b>Tajriba:</b>
{exp_map.get(experience, '⚪️ Muhim emas')}

🌐 <b>Manbalar:</b>
{', '.join(sources_text) if sources_text else '🌐 hh.uz'}
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_settings")]
            ]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


# ========== KALIT SO'ZLAR ==========

@router.callback_query(F.data == "set_keywords")
async def set_keywords_start(callback: CallbackQuery, state: FSMContext):
    """Kalit so'zlarni sozlash"""
    text = """
🔑 <b>Kalit so'zlar</b>

Qidiruv uchun kalit so'zlarni kiriting.

<b>Misol:</b>
<code>python, django, backend</code>

Yoki /cancel bekor qilish
"""
    
    await callback.message.edit_text(text, parse_mode='HTML')
    await state.set_state(SettingsStates.waiting_for_keywords)
    await callback.answer()


@router.message(SettingsStates.waiting_for_keywords)
async def process_keywords(message: Message, state: FSMContext):
    """Kalit so'zlarni qayta ishlash"""
    user_id = message.from_user.id
    
    try:
        text = message.text.strip()
        
        if not text:
            await message.answer("❌ Kalit so'z kiritilmadi.")
            return
        
        keywords = [k.strip() for k in text.replace(',', ' ').split() if k.strip()]
        
        user_filter = await db.get_user_filter(user_id) or {}
        user_filter['keywords'] = keywords
        
        success = await db.save_user_filter(user_id, user_filter)
        
        if success:
            await message.answer(
                f"✅ <b>Kalit so'zlar saqlandi!</b>\n\n"
                f"🔑 {', '.join(keywords)}\n\n"
                f"Endi boshqa sozlamalarni o'rnating:",
                reply_markup=get_settings_keyboard(await db.is_premium(user_id)),
                parse_mode='HTML'
            )
        else:
            await message.answer("❌ Xatolik yuz berdi! Qaytadan urinib ko'ring.", parse_mode='HTML')
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"process_keywords error for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi! Iltimos, qaytadan urinib ko'ring.", parse_mode='HTML')
        await state.clear()


# ========== JOYLASHUV ==========

@router.callback_query(F.data == "set_locations")
async def set_locations_start(callback: CallbackQuery, state: FSMContext):
    """Joylashuvni sozlash"""
    text = """
📍 <b>Joylashuv</b>

Shahar(lar)ni kiriting.

<b>Misol:</b>
<code>Toshkent</code>

Yoki /cancel bekor qilish
"""
    
    await callback.message.edit_text(text, parse_mode='HTML')
    await state.set_state(SettingsStates.waiting_for_locations)
    await callback.answer()


@router.message(SettingsStates.waiting_for_locations)
async def process_locations(message: Message, state: FSMContext):
    """Joylashuvni qayta ishlash"""
    user_id = message.from_user.id
    
    try:
        text = message.text.strip()
        
        if not text:
            await message.answer("❌ Joylashuv kiritilmadi.")
            return
        
        locations = [l.strip().title() for l in text.replace(',', ' ').split() if l.strip()]
        
        user_filter = await db.get_user_filter(user_id) or {}
        user_filter['locations'] = locations
        
        success = await db.save_user_filter(user_id, user_filter)
        
        if success:
            await message.answer(
                f"✅ <b>Joylashuv saqlandi!</b>\n\n"
                f"📍 {', '.join(locations)}\n\n"
                f"Endi boshqa sozlamalarni o'rnating:",
                reply_markup=get_settings_keyboard(await db.is_premium(user_id)),
                parse_mode='HTML'
            )
        else:
            await message.answer("❌ Xatolik yuz berdi! Qaytadan urinib ko'ring.", parse_mode='HTML')
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"process_locations error for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi! Iltimos, qaytadan urinib ko'ring.", parse_mode='HTML')
        await state.clear()


# ========== MAOSH - FIXED VERSION ==========

@router.callback_query(F.data == "set_salary")
async def set_salary_start(callback: CallbackQuery, state: FSMContext):
    """Maoshni sozlash - FIXED"""
    # ❌ MUAMMO: user_id state'ga saqlanmagan edi
    # ✅ YECHIM: Har doim message.from_user.id ishlatish
    
    text = """
💰 <b>Maosh</b>

Minimal maoshni kiriting (so'm):

<b>Misol:</b> <code>3000000</code>

Yoki /skip o'tkazish uchun
"""
    
    await callback.message.edit_text(text, parse_mode='HTML')
    await state.set_state(SettingsStates.waiting_for_min_salary)
    await callback.answer()


@router.message(SettingsStates.waiting_for_min_salary)
async def process_min_salary(message: Message, state: FSMContext):
    """Minimal maoshni qayta ishlash - FIXED"""
    # ✅ YECHIM: user_id to'g'ridan-to'g'ri message'dan olish
    user_id = message.from_user.id
    
    try:
        if message.text.strip() == "/skip":
            min_salary = None
            await state.update_data(salary_min=None)
        else:
            try:
                min_salary = int(message.text.strip().replace(' ', '').replace(',', ''))
                if min_salary < 0:
                    await message.answer("❌ Maosh musbat bo'lishi kerak!")
                    return
                await state.update_data(salary_min=min_salary)
            except ValueError:
                await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
                return
        
        await message.answer("💰 Maksimal maoshni kiriting yoki /skip:", parse_mode='HTML')
        await state.set_state(SettingsStates.waiting_for_max_salary)
        
    except Exception as e:
        logger.error(f"[MIN_SALARY] Error for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi!")
        await state.clear()


@router.message(SettingsStates.waiting_for_max_salary)
async def process_max_salary(message: Message, state: FSMContext):
    """Maksimal maoshni qayta ishlash - FIXED"""
    # ✅ YECHIM: user_id to'g'ridan-to'g'ri message'dan olish
    user_id = message.from_user.id
    
    try:
        # State'dan minimal maoshni olish
        data = await state.get_data()
        min_salary = data.get('salary_min')
        
        if message.text.strip() == "/skip":
            max_salary = None
        else:
            try:
                max_salary = int(message.text.strip().replace(' ', '').replace(',', ''))
                if max_salary < 0:
                    await message.answer("❌ Maosh musbat bo'lishi kerak!")
                    return
                if min_salary and max_salary < min_salary:
                    await message.answer(
                        f"❌ Maksimal maosh ({max_salary:,}) minimal maoshdan ({min_salary:,}) kichik bo'lmasligi kerak!\n\n"
                        "Qaytadan kiriting yoki /skip:",
                        parse_mode='HTML'
                    )
                    return
            except ValueError:
                await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
                return
        
        # Database'ga saqlash
        user_filter = await db.get_user_filter(user_id) or {}
        user_filter['salary_min'] = min_salary
        user_filter['salary_max'] = max_salary
        
        success = await db.save_user_filter(user_id, user_filter)
        
        if success:
            salary_text = ""
            if min_salary and max_salary:
                salary_text = f"{min_salary:,} - {max_salary:,} so'm"
            elif min_salary:
                salary_text = f"dan {min_salary:,} so'm"
            elif max_salary:
                salary_text = f"gacha {max_salary:,} so'm"
            else:
                salary_text = "Ko'rsatilmagan"
            
            await message.answer(
                f"✅ <b>Maosh saqlandi!</b>\n\n"
                f"💰 {salary_text}\n\n"
                f"Endi boshqa sozlamalarni o'rnating:",
                reply_markup=get_settings_keyboard(await db.is_premium(user_id)),
                parse_mode='HTML'
            )
        else:
            await message.answer("❌ Xatolik yuz berdi! Qaytadan urinib ko'ring.", parse_mode='HTML')
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"[MAX_SALARY] Error for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi!\n\nIltimos, qaytadan urinib ko'ring yoki /cancel", parse_mode='HTML')
        await state.clear()


# ========== TAJRIBA ==========

@router.callback_query(F.data == "set_experience")
async def set_experience_start(callback: CallbackQuery):
    """Tajribani sozlash"""
    await callback.message.edit_text(
        "👔 <b>Tajriba darajasi</b>",
        reply_markup=get_experience_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exp_"))
async def process_experience(callback: CallbackQuery):
    """Tajribani qayta ishlash"""
    user_id = callback.from_user.id
    experience = callback.data.replace("exp_", "")
    
    try:
        user_filter = await db.get_user_filter(user_id) or {}
        user_filter['experience_level'] = experience
        
        success = await db.save_user_filter(user_id, user_filter)
        
        exp_map = {
            'no_experience': '🟢 Tajribasiz',
            'between_1_and_3': '🟡 1-3 yil',
            'between_3_and_6': '🟠 3-6 yil',
            'more_than_6': '🔴 6+ yil',
            'not_specified': '⚪️ Muhim emas'
        }
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Tajriba saqlandi!</b>\n\n"
                f"👔 {exp_map.get(experience, 'N/A')}\n\n"
                f"Endi boshqa sozlamalarni o'rnating:",
                reply_markup=get_settings_keyboard(await db.is_premium(user_id)),
                parse_mode='HTML'
            )
        else:
            await callback.message.edit_text("❌ Xatolik yuz berdi!", parse_mode='HTML')
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"process_experience error for user {user_id}: {e}", exc_info=True)
        await callback.answer("❌ Xatolik!", show_alert=True)


# ========== MANBALAR ==========

@router.callback_query(F.data == "set_sources")
async def set_sources(callback: CallbackQuery, state: FSMContext):
    """Manbalarni sozlash"""
    is_premium = await db.is_premium(callback.from_user.id)
    user_filter = await db.get_user_filter(callback.from_user.id) or {}
    
    current_sources = user_filter.get('sources', ['hh_uz', 'user_post'])
    
    if 'user_post' not in current_sources:
        current_sources.append('user_post')
    
    await state.update_data(temp_sources=current_sources.copy())
    
    text = """
🌐 <b>Qidiruv manbalari</b>

Vakansiyalarni qayerdan qidirishni tanlang:

🌐 <b>hh.uz</b> - Eng katta vakansiya sayti
📢 <b>Bot e'lonlar</b> - Foydalanuvchilar e'lonlari (avtomatik)
📱 <b>Telegram</b> - Telegram kanallaridan (Premium)

Bir yoki bir nechta manbani tanlashingiz mumkin.
"""
    
    if not is_premium:
        text += "\n\n💡 <b>Premium</b> obuna bilan Telegram kanallaridan ham qidirishingiz mumkin!"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_sources_keyboard(is_premium, current_sources),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_source_"))
async def toggle_source(callback: CallbackQuery, state: FSMContext):
    """Manbani yoqish/o'chirish"""
    source = callback.data.replace("toggle_source_", "")
    
    data = await state.get_data()
    temp_sources = data.get('temp_sources', ['hh_uz', 'user_post'])
    
    if source in temp_sources:
        if len(temp_sources) > 1 and source != 'user_post':
            temp_sources.remove(source)
    else:
        temp_sources.append(source)
    
    await state.update_data(temp_sources=temp_sources)
    
    is_premium = await db.is_premium(callback.from_user.id)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_sources_keyboard(is_premium, temp_sources)
        )
    except:
        pass
    
    await callback.answer()


@router.callback_query(F.data == "save_sources")
async def save_sources(callback: CallbackQuery, state: FSMContext):
    """Manbalarni saqlash"""
    user_id = callback.from_user.id
    data = await state.get_data()
    temp_sources = data.get('temp_sources', ['hh_uz', 'user_post'])
    
    if 'user_post' not in temp_sources:
        temp_sources.append('user_post')
    
    try:
        user_filter = await db.get_user_filter(user_id) or {}
        user_filter['sources'] = temp_sources
        
        success = await db.save_user_filter(user_id, user_filter)
        
        if success:
            sources_text = []
            if 'hh_uz' in temp_sources:
                sources_text.append('🌐 hh.uz')
            if 'user_post' in temp_sources:
                sources_text.append('📢 Bot e\'lonlar')
            if 'telegram' in temp_sources:
                sources_text.append('📱 Telegram')
            
            await callback.message.edit_text(
                f"✅ <b>Manbalar saqlandi!</b>\n\n"
                f"{', '.join(sources_text)}",
                parse_mode='HTML'
            )
        else:
            await callback.message.edit_text("❌ Xatolik yuz berdi!", parse_mode='HTML')
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"save_sources error for user {user_id}: {e}", exc_info=True)
        await callback.answer("❌ Xatolik!", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "info_user_post")
async def info_user_post(callback: CallbackQuery):
    """User post haqida ma'lumot"""
    await callback.answer(
        "📢 Bot e'lonlar - Premium foydalanuvchilar tomonidan botga joylangan vakansiyalar. "
        "Bu manba avtomatik yoniq va o'chirib bo'lmaydi.",
        show_alert=True
    )


@router.callback_query(F.data == "need_premium")
async def need_premium(callback: CallbackQuery):
    """Premium kerak xabari"""
    await callback.answer(
        "💎 Telegram kanallaridan qidirish faqat Premium foydalanuvchilar uchun!\n\n"
        "Premium bo'limiga o'ting.",
        show_alert=True
    )


@router.callback_query(F.data == "upload_cv_info")
async def upload_cv_info(callback: CallbackQuery):
    """CV yuklash haqida ma'lumot"""
    text = """
📄 <b>CV orqali avtomatik sozlash</b>

Bot sizning Rezyume (CV) faylingizni tahlil qilib, kerakli ko'nikmalar va tajribani avtomatik aniqlab beradi.

<b>Yo'riqnoma:</b>
1. Shu xabarga javoban CV faylingizni yuboring.
2. Format: <b>PDF</b> yoki <b>Word (DOCX)</b>.
3. Bot faylni o'qiydi va sozlamalarni o'zi to'g'irlaydi.

<i>Hozirning o'zida faylni tashlashingiz mumkin!</i> 👇
"""
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_settings")]
            ]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


# ========== TOZALASH ==========

@router.callback_query(F.data == "clear_settings")
async def clear_settings(callback: CallbackQuery):
    """Sozlamalarni tozalash"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data="confirm_clear"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="back_to_settings")
            ]
        ]
    )
    
    await callback.message.edit_text(
        "⚠️ Barcha sozlamalarni tozalashni xohlaysizmi?",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear")
async def confirm_clear_settings(callback: CallbackQuery):
    """Tozalashni tasdiqlash"""
    try:
        await db.delete_user_filter(callback.from_user.id)
        await callback.message.edit_text("✅ <b>Sozlamalar tozalandi!</b>", parse_mode='HTML')
        await callback.answer()
    except Exception as e:
        logger.error(f"clear_settings error: {e}")
        await callback.answer("❌ Xatolik!", show_alert=True)


@router.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "/cancel")
async def cancel_action(message: Message, state: FSMContext):
    """Bekor qilish"""
    await state.clear()
    await message.answer("❌ Bekor qilindi")
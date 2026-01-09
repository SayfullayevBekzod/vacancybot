from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()


def get_favorite_keyboard(vacancy_id: str):
    """Vakansiya uchun saqlash tugmasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💾 Saqlash",
                    callback_data=f"save_favorite_{vacancy_id}"
                ),
                InlineKeyboardButton(
                    text="📄 To'liq",
                    callback_data=f"view_full_{vacancy_id}"
                )
            ]
        ]
    )


def get_saved_list_keyboard(page: int = 0, total_pages: int = 1):
    """Saqlangan vakansiyalar ro'yxati klaviaturasi"""
    buttons = []
    
    # Navigatsiya
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"saved_page_{page-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="saved_info")
    )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"saved_page_{page+1}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Boshqa tugmalar
    buttons.extend([
        [
            InlineKeyboardButton(text="🗑 Hammasini o'chirish", callback_data="clear_all_favorites"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_favorites")
        ],
        [
            InlineKeyboardButton(text="🔙 Yopish", callback_data="close_favorites")
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.text == "💾 Saqlangan")
async def cmd_favorites(message: Message):
    """Saqlangan vakansiyalar"""
    try:
        # Saqlangan vakansiyalarni olish
        async with db.pool.acquire() as conn:
            favorites = await conn.fetch('''
                SELECT 
                    sv.vacancy_id,
                    sv.vacancy_title,
                    sv.sent_at,
                    v.title,
                    v.company,
                    v.location,
                    v.salary_min,
                    v.salary_max,
                    v.url,
                    v.source
                FROM sent_vacancies sv
                LEFT JOIN vacancies v ON sv.vacancy_id = v.vacancy_id
                WHERE sv.user_id = $1
                ORDER BY sv.sent_at DESC
                LIMIT 5
            ''', message.from_user.id)
            
            total = await conn.fetchval('SELECT COUNT(*) FROM sent_vacancies WHERE user_id = $1', message.from_user.id)
            total_pages = (total + 4) // 5
        
        if not favorites:
            await message.answer(
                "💾 <b>Saqlangan vakansiyalar</b>\n\n"
                "Sizda hali saqlangan vakansiyalar yo'q.\n\n"
                "💡 Vakansiyani saqlash uchun:\n"
                "1. Vakansiya qidiring\n"
                "2. '💾 Saqlash' tugmasini bosing",
                parse_mode='HTML'
            )
            return
        
        text = f"💾 <b>Saqlangan vakansiyalar</b>\n\n"
        text += f"📊 Jami: <b>{total}</b> ta\n\n"
        
        for i, fav in enumerate(favorites, 1):
            title = fav['title'] or fav['vacancy_title'] or 'Vakansiya'
            company = fav['company'] or 'Kompaniya'
            location = fav['location'] or 'Joylashuv'
            
            text += f"{i}. <b>{title}</b>\n"
            text += f"   🏢 {company}\n"
            text += f"   📍 {location}\n"
            text += f"   🔗 /view_{fav['vacancy_id']}\n\n"
        
        await message.answer(
            text,
            reply_markup=get_saved_list_keyboard(0, total_pages),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Favorites error: {e}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi")


@router.callback_query(F.data.startswith("save_favorite_"))
async def save_favorite(callback: CallbackQuery):
    """Vakansiyani saqlash"""
    try:
        vacancy_id = callback.data.replace("save_favorite_", "")
        
        # Saqlash
        success = await db.add_sent_vacancy(
            callback.from_user.id, 
            vacancy_id, 
            "Saved by user"
        )
        
        if success:
            await callback.answer("✅ Vakansiya saqlandi!", show_alert=True)
            logger.info(f"User {callback.from_user.id} saved vacancy {vacancy_id}")
        else:
            await callback.answer("⚠️ Allaqachon saqlangan", show_alert=True)
            
    except Exception as e:
        logger.error(f"Save favorite error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("unsave_favorite_"))
async def unsave_favorite(callback: CallbackQuery):
    """Vakansiyani o'chirish"""
    try:
        vacancy_id = callback.data.replace("unsave_favorite_", "")
        
        async with db.pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM sent_vacancies
                WHERE user_id = $1 AND vacancy_id = $2
            ''', callback.from_user.id, vacancy_id)
        
        await callback.answer("🗑 O'chirildi", show_alert=True)
        
        # Ro'yxatni yangilash
        await refresh_favorites(callback)
        
    except Exception as e:
        logger.error(f"Unsave favorite error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data == "clear_all_favorites")
async def clear_all_favorites(callback: CallbackQuery):
    """Hammasini o'chirish"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_clear_favorites"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="refresh_favorites")
            ]
        ]
    )
    
    await callback.message.edit_text(
        "⚠️ <b>Barcha saqlangan vakansiyalarni o'chirasizmi?</b>\n\n"
        "Bu amal qaytarib bo'lmaydi!",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_favorites")
async def confirm_clear_favorites(callback: CallbackQuery):
    """Tozalashni tasdiqlash"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM sent_vacancies
                WHERE user_id = $1
            ''', callback.from_user.id)
        
        await callback.message.edit_text(
            "✅ <b>Barcha saqlangan vakansiyalar o'chirildi</b>",
            parse_mode='HTML'
        )
        await callback.answer("🗑 O'chirildi", show_alert=True)
        
    except Exception as e:
        logger.error(f"Clear favorites error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data == "refresh_favorites")
async def refresh_favorites(callback: CallbackQuery):
    """Yangilash"""
    try:
        async with db.pool.acquire() as conn:
            favorites = await conn.fetch('''
                SELECT sv.vacancy_id, sv.vacancy_title, v.title, v.company, v.location, v.salary_min, v.salary_max
                FROM sent_vacancies sv
                LEFT JOIN vacancies v ON sv.vacancy_id = v.vacancy_id
                WHERE sv.user_id = $1
                ORDER BY sv.sent_at DESC
                LIMIT 5
            ''', callback.from_user.id)
            
            total = await db.pool.fetchval('SELECT COUNT(*) FROM sent_vacancies WHERE user_id = $1', callback.from_user.id)
            total_pages = (total + 4) // 5
        
        if not favorites:
            await callback.message.edit_text(
                "💾 <b>Saqlangan vakansiyalar</b>\n\n"
                "Sizda hali saqlangan vakansiyalar yo'q.",
                parse_mode='HTML'
            )
            return
        
        text = f"💾 <b>Saqlangan vakansiyalar</b>\n\n"
        text += f"📊 Jami: <b>{total}</b> ta\n\n"
        
        for i, fav in enumerate(favorites, 1):
            title = fav['title'] or fav['vacancy_title'] or 'Vakansiya'
            company = fav['company'] or 'Kompaniya'
            text += f"{i}. <b>{title}</b>\n   🏢 {company}\n   🔗 /view_{fav['vacancy_id']}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_saved_list_keyboard(0, total_pages),
            parse_mode='HTML'
        )
        await callback.answer("✅ Yangilandi")
    except Exception as e:
        logger.error(f"Refresh favorites error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("saved_page_"))
async def saved_page(callback: CallbackQuery):
    """Sahifani almashtirish"""
    try:
        page = int(callback.data.replace("saved_page_", ""))
        async with db.pool.acquire() as conn:
            favorites = await conn.fetch('''
                SELECT sv.vacancy_id, sv.vacancy_title, v.title, v.company, v.location, v.salary_min, v.salary_max
                FROM sent_vacancies sv
                LEFT JOIN vacancies v ON sv.vacancy_id = v.vacancy_id
                WHERE sv.user_id = $1
                ORDER BY sv.sent_at DESC
                LIMIT 5 OFFSET $2
            ''', callback.from_user.id, page * 5)
            total = await db.pool.fetchval('SELECT COUNT(*) FROM sent_vacancies WHERE user_id = $1', callback.from_user.id)
            total_pages = (total + 4) // 5
        
        if not favorites:
            await callback.answer("Boshqa natija yo'q")
            return
            
        text = f"💾 <b>Saqlangan vakansiyalar</b>\n\n📊 Jami: <b>{total}</b> ta\n\n"
        for i, fav in enumerate(favorites, page * 5 + 1):
            title = fav['title'] or fav['vacancy_title'] or 'Vakansiya'
            company = fav['company'] or 'Kompaniya'
            text += f"{i}. <b>{title}</b>\n   🏢 {company}\n   🔗 /view_{fav['vacancy_id']}\n\n"
            
        await callback.message.edit_text(text, reply_markup=get_saved_list_keyboard(page, total_pages), parse_mode='HTML')
        await callback.answer()
    except Exception as e:
        logger.error(f"saved_page error: {e}")
        await callback.answer("❌ Xatolik")


@router.callback_query(F.data.startswith("view_full_"))
async def view_full_saved(callback: CallbackQuery):
    """Saqlangan vakansiyani to'liq ko'rish"""
    try:
        vacancy_id = callback.data.replace("view_full_", "")
        vac = await db.get_vacancy(vacancy_id)
        if not vac:
            await callback.answer("⚠️ Vakansiya topilmadi", show_alert=True)
            return
            
        from filters import vacancy_filter
        text = vacancy_filter.format_vacancy_message(vac)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"unsave_favorite_{vacancy_id}")],
            [InlineKeyboardButton(text="🔙 Ro'yxatga", callback_data="refresh_favorites")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await callback.answer()
    except Exception as e:
        logger.error(f"view_full_saved error: {e}")
        await callback.answer("❌ Xatolik")


@router.callback_query(F.data == "close_favorites")
async def close_favorites(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()
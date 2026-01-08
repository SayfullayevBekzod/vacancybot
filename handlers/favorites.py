from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from filters import vacancy_filter
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
                LIMIT 50
            ''', message.from_user.id)
        
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
        
        # Birinchi 5 tani ko'rsatish
        text = f"💾 <b>Saqlangan vakansiyalar</b>\n\n"
        text += f"📊 Jami: <b>{len(favorites)}</b> ta\n\n"
        
        for i, fav in enumerate(favorites[:5], 1):
            title = fav['title'] or fav['vacancy_title'] or 'Vakansiya'
            company = fav['company'] or 'Kompaniya'
            location = fav['location'] or 'Joylashuv'
            
            text += f"{i}. <b>{title}</b>\n"
            text += f"   🏢 {company}\n"
            text += f"   📍 {location}\n"
            
            if fav['salary_min'] or fav['salary_max']:
                salary = ""
                if fav['salary_min']:
                    salary += f"{fav['salary_min']:,}"
                if fav['salary_max']:
                    salary += f" - {fav['salary_max']:,}"
                text += f"   💰 {salary} so'm\n"
            
            text += f"   🔗 /view_{fav['vacancy_id']}\n\n"
        
        if len(favorites) > 5:
            text += f"... va yana {len(favorites) - 5} ta\n\n"
        
        text += "💡 Vakansiyani ko'rish uchun linkni bosing yoki ID kiriting"
        
        await message.answer(
            text,
            reply_markup=get_saved_list_keyboard(0, (len(favorites) + 4) // 5),
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
        await callback.message.edit_text(
            "🗑 Vakansiya o'chirildi\n\n"
            "💾 Saqlangan vakansiyalarni ko'rish uchun qaytadan bosing.",
            parse_mode='HTML'
        )
        
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
            result = await conn.execute('''
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
    # Xuddi cmd_favorites kabi, lekin callback uchun
    try:
        async with db.pool.acquire() as conn:
            favorites = await conn.fetch('''
                SELECT 
                    sv.vacancy_id,
                    sv.vacancy_title,
                    v.title,
                    v.company,
                    v.location,
                    v.salary_min,
                    v.salary_max
                FROM sent_vacancies sv
                LEFT JOIN vacancies v ON sv.vacancy_id = v.vacancy_id
                WHERE sv.user_id = $1
                ORDER BY sv.sent_at DESC
                LIMIT 50
            ''', callback.from_user.id)
        
        if not favorites:
            await callback.message.edit_text(
                "💾 <b>Saqlangan vakansiyalar</b>\n\n"
                "Sizda hali saqlangan vakansiyalar yo'q.",
                parse_mode='HTML'
            )
            return
        
        text = f"💾 <b>Saqlangan vakansiyalar</b>\n\n"
        text += f"📊 Jami: <b>{len(favorites)}</b> ta\n\n"
        
        for i, fav in enumerate(favorites[:5], 1):
            title = fav['title'] or fav['vacancy_title'] or 'Vakansiya'
            company = fav['company'] or 'Kompaniya'
            
            text += f"{i}. <b>{title}</b>\n"
            text += f"   🏢 {company}\n\n"
        
        if len(favorites) > 5:
            text += f"... va yana {len(favorites) - 5} ta"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_saved_list_keyboard(0, (len(favorites) + 4) // 5),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Refresh favorites error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer("✅ Yangilandi")


@router.callback_query(F.data == "close_favorites")
async def close_favorites(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()
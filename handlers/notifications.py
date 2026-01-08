from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()


def get_notifications_keyboard(is_enabled: bool):
    """Bildirishnomalar klaviaturasi"""
    status_text = "🔔 Yoniq" if is_enabled else "🔕 O'chiq"
    toggle_text = "🔕 O'chirish" if is_enabled else "🔔 Yoqish"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data="toggle_notifications"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Sozlamalar",
                    callback_data="notification_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="notification_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="close_notifications"
                )
            ]
        ]
    )


def get_notification_settings_keyboard(settings: dict):
    """Bildirishnoma sozlamalari"""
    instant = settings.get('instant_notify', True)
    daily = settings.get('daily_digest', False)
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if instant else '☐'} Darhol xabar",
                    callback_data="toggle_instant_notify"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✅' if daily else '☐'} Kunlik xulosa",
                    callback_data="toggle_daily_digest"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Vaqtni sozlash",
                    callback_data="set_notification_time"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💾 Saqlash",
                    callback_data="save_notification_settings"
                ),
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="show_notifications"
                )
            ]
        ]
    )


@router.message(F.text == "🔔 Bildirishnomalar")
async def cmd_notifications(message: Message):
    """Bildirishnomalar sozlamalari"""
    # Premium tekshirish
    is_premium = await db.is_premium(message.from_user.id)
    
    if not is_premium:
        await message.answer(
            "🔒 <b>Premium xususiyat!</b>\n\n"
            "Push bildirishnomalar faqat Premium foydalanuvchilar uchun.\n\n"
            "💎 Premium bilan:\n"
            "• Yangi vakansiya chiqqanda darhol xabar\n"
            "• Kunlik xulosa (digest)\n"
            "• O'zingizga mos vakansiyalar\n"
            "• Spam yo'q, faqat kerakli xabarlar\n\n"
            "Premium sotib olish uchun 💎 Premium tugmasini bosing.",
            parse_mode='HTML'
        )
        return
    
    # Bildirishnomalar holati
    async with db.pool.acquire() as conn:
        settings = await conn.fetchrow('''
            SELECT * FROM notification_settings
            WHERE user_id = $1
        ''', message.from_user.id)
    
    is_enabled = settings.get('enabled', True) if settings else True
    
    status_emoji = "🔔" if is_enabled else "🔕"
    status_text = "yoniq" if is_enabled else "o'chiq"
    
    text = f"{status_emoji} <b>Push Bildirishnomalar</b>\n\n"
    text += f"Hozirgi holat: <b>{status_text}</b>\n\n"
    
    if is_enabled:
        text += "✅ Sizga mos yangi vakansiyalar chiqqanda darhol xabar beramiz!\n\n"
        
        if settings:
            if settings.get('instant_notify'):
                text += "• 🔔 Darhol xabar: Yoniq\n"
            if settings.get('daily_digest'):
                text += "• 📊 Kunlik xulosa: Yoniq\n"
    else:
        text += "⚠️ Bildirishnomalar o'chirilgan. Yangi vakansiyalar haqida xabar olmaysiz.\n\n"
    
    text += "\n💡 Sozlamalarni o'zgartiring:"
    
    await message.answer(
        text,
        reply_markup=get_notifications_keyboard(is_enabled),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "show_notifications")
async def show_notifications(callback: CallbackQuery):
    """Bildirishnomalarni ko'rsatish"""
    async with db.pool.acquire() as conn:
        settings = await conn.fetchrow('''
            SELECT * FROM notification_settings
            WHERE user_id = $1
        ''', callback.from_user.id)
    
    is_enabled = settings.get('enabled', True) if settings else True
    
    status_emoji = "🔔" if is_enabled else "🔕"
    status_text = "yoniq" if is_enabled else "o'chiq"
    
    text = f"{status_emoji} <b>Push Bildirishnomalar</b>\n\n"
    text += f"Hozirgi holat: <b>{status_text}</b>\n\n"
    
    if is_enabled:
        text += "✅ Yangi vakansiyalar haqida xabar beramiz!\n\n"
    else:
        text += "⚠️ Bildirishnomalar o'chirilgan.\n\n"
    
    text += "💡 Sozlamalarni o'zgartiring:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_notifications_keyboard(is_enabled),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Bildirishnomalarni yoqish/o'chirish"""
    try:
        async with db.pool.acquire() as conn:
            # Hozirgi holat
            current = await conn.fetchrow('''
                SELECT enabled FROM notification_settings
                WHERE user_id = $1
            ''', callback.from_user.id)
            
            if current:
                new_state = not current['enabled']
                await conn.execute('''
                    UPDATE notification_settings
                    SET enabled = $2
                    WHERE user_id = $1
                ''', callback.from_user.id, new_state)
            else:
                new_state = False
                await conn.execute('''
                    INSERT INTO notification_settings (user_id, enabled)
                    VALUES ($1, $2)
                ''', callback.from_user.id, new_state)
        
        status_text = "yoqildi" if new_state else "o'chirildi"
        await callback.answer(f"✅ Bildirishnomalar {status_text}", show_alert=True)
        
        # Yangilash
        await show_notifications(callback)
        
    except Exception as e:
        logger.error(f"Toggle notifications error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data == "notification_settings")
async def notification_settings(callback: CallbackQuery):
    """Bildirishnoma sozlamalari"""
    async with db.pool.acquire() as conn:
        settings = await conn.fetchrow('''
            SELECT * FROM notification_settings
            WHERE user_id = $1
        ''', callback.from_user.id)
    
    settings_dict = dict(settings) if settings else {
        'instant_notify': True,
        'daily_digest': False
    }
    
    text = "⚙️ <b>Bildirishnoma sozlamalari</b>\n\n"
    text += "🔔 <b>Darhol xabar:</b>\n"
    text += "Yangi vakansiya chiqqanda darhol xabar berish\n\n"
    text += "📊 <b>Kunlik xulosa:</b>\n"
    text += "Har kuni kechqurun kunlik vakansiyalar xulasasi\n\n"
    text += "Kerakli sozlamalarni tanlang:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_notification_settings_keyboard(settings_dict),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "notification_stats")
async def notification_stats(callback: CallbackQuery):
    """Bildirishnoma statistikasi"""
    try:
        async with db.pool.acquire() as conn:
            # Oxirgi 7 kundagi bildirishnomalar
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE sent_at > NOW() - INTERVAL '24 hours') as today,
                    COUNT(*) FILTER (WHERE sent_at > NOW() - INTERVAL '7 days') as week
                FROM sent_vacancies
                WHERE user_id = $1
            ''', callback.from_user.id)
        
        text = "📊 <b>Bildirishnoma statistikasi</b>\n\n"
        text += f"📅 Bugun: <b>{stats['today']}</b> ta\n"
        text += f"📅 Oxirgi 7 kun: <b>{stats['week']}</b> ta\n"
        text += f"📅 Jami: <b>{stats['total']}</b> ta\n\n"
        text += "💡 Bildirishnomalar faqat sizning filtrlaringizga mos vakansiyalar uchun yuboriladi."
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_notifications")]
                ]
            ),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Notification stats error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "close_notifications")
async def close_notifications(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()
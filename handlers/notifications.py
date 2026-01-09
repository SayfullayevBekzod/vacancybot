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


@router.callback_query(F.data == "toggle_instant_notify")
async def toggle_instant_notify(callback: CallbackQuery):
    """Darhol xabarni yoqish/o'chirish"""
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow('SELECT instant_notify FROM notification_settings WHERE user_id = $1', callback.from_user.id)
            new_val = not (settings['instant_notify'] if settings else True)
            
            await conn.execute('''
                INSERT INTO notification_settings (user_id, instant_notify)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET instant_notify = EXCLUDED.instant_notify, updated_at = NOW()
            ''', callback.from_user.id, new_val)
            
        await notification_settings(callback)
    except Exception as e:
        logger.error(f"toggle_instant_notify error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data == "toggle_daily_digest")
async def toggle_daily_digest(callback: CallbackQuery):
    """Kunlik xulosani yoqish/o'chirish"""
    try:
        async with db.pool.acquire() as conn:
            settings = await conn.fetchrow('SELECT daily_digest FROM notification_settings WHERE user_id = $1', callback.from_user.id)
            new_val = not (settings['daily_digest'] if settings else False)
            
            await conn.execute('''
                INSERT INTO notification_settings (user_id, daily_digest)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET daily_digest = EXCLUDED.daily_digest, updated_at = NOW()
            ''', callback.from_user.id, new_val)
            
        await notification_settings(callback)
    except Exception as e:
        logger.error(f"toggle_daily_digest error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data == "save_notification_settings")
async def save_notification_settings(callback: CallbackQuery):
    """Sozlamalarni saqlash va orqaga"""
    await callback.answer("✅ Sozlamalar saqlandi!")
    await show_notifications(callback)

@router.callback_query(F.data == "set_notification_time")
async def set_notification_time(callback: CallbackQuery):
    """Vaqtni tanlash klaviaturasi (sodda versiya)"""
    times = ["08:00", "12:00", "18:00", "20:00", "22:00"]
    buttons = []
    row = []
    for t in times:
        row.append(InlineKeyboardButton(text=t, callback_data=f"set_time_{t}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="notification_settings")])
    
    await callback.message.edit_text(
        "⏰ <b>Xulosa vaqtini tanlang:</b>\n\n"
        "Kunlik xulosa qaysi vaqtda yuborilsin?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_time_"))
async def save_notification_time(callback: CallbackQuery):
    """Vaqtni saqlash"""
    new_time = callback.data.replace("set_time_", "")
    try:
        async with db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO notification_settings (user_id, digest_time)
                VALUES ($1, $2::TIME)
                ON CONFLICT (user_id) DO UPDATE SET digest_time = EXCLUDED.digest_time, updated_at = NOW()
            ''', callback.from_user.id, new_time)
        
        await callback.answer(f"✅ Vaqt {new_time} ga o'rnatildi")
        await notification_settings(callback)
    except Exception as e:
        logger.error(f"save_notification_time error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data == "close_notifications")
async def close_notifications(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()

async def send_daily_digests():
    """Kunlik xulosalarni yuborish"""
    from loader import bot
    logger.info("📅 Kunlik xulosalar yuborish boshlandi...")
    
    users = await db.get_users_for_digest()
    if not users:
        logger.info("   Hozircha yuboriladigan xulosa yo'q")
        return
        
    for user_row in users:
        user_id = user_row['user_id']
        try:
            vacancies = await db.get_recent_vacancies_for_user(user_id, limit=5)
            if not vacancies:
                continue
                
            text = f"📅 <b>Kunlik xulosa</b>\n\n"
            text += f"Oxirgi 24 soat ichida sizga mos <b>{len(vacancies)}</b> ta yangi vakansiya topildi:\n\n"
            
            for i, vac in enumerate(vacancies, 1):
                text += f"{i}. <b>{vac['title']}</b>\n"
                text += f"   🏢 {vac['company']}\n"
                text += f"   🔗 /view_{vac['vacancy_id']}\n\n"
            
            text += "💡 Batafsil ma'lumot uchun linkni bosing."
            
            await bot.send_message(user_id, text, parse_mode='HTML')
            await db.update_last_digest_sent(user_id)
            await asyncio.sleep(0.3)
            
        except Exception as e:
            logger.error(f"Error sending digest to {user_id}: {e}")
    
    logger.info(f"✅ Kunlik xulosalar {len(users)} ta userga yuborildi")

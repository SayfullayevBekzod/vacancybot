from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from config import PREMIUM_FEATURES, PREMIUM_PRICE, ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

router = Router()


# FSM States
class PremiumStates(StatesGroup):
    waiting_for_payment_proof = State()
    waiting_for_plan_selection = State()


def get_premium_keyboard():
    """Premium klaviatura"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Premium sotib olish",
                    callback_data="buy_premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Tariflar",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="close_premium"
                )
            ]
        ]
    )
    return keyboard


def get_plans_keyboard():
    """Tariflar klaviaturasi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📅 1 oy - {PREMIUM_PRICE['monthly']:,} so'm",
                    callback_data="plan_monthly"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📆 1 yil - {PREMIUM_PRICE['yearly']:,} so'm",
                    callback_data="plan_yearly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="show_premium"
                )
            ]
        ]
    )
    return keyboard


def get_payment_confirm_keyboard(user_id: int, days: int):
    """Admin uchun tasdiqlash klaviaturasi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"approve_payment_{user_id}_{days}"
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"reject_payment_{user_id}_{days}"
                )
            ]
        ]
    )
    return keyboard


@router.message(F.text == "💎 Premium")
async def cmd_premium(message: Message):
    """Premium bo'limi"""
    is_premium = await db.is_premium(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    
    if is_premium:
        premium_until = user.get('premium_until')
        if premium_until:
            date_str = premium_until.strftime('%d.%m.%Y')
            time_str = premium_until.strftime('%H:%M')
            
            # Qancha kun qolganini hisoblash
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if premium_until.tzinfo is None:
                premium_until = premium_until.replace(tzinfo=timezone.utc)
            
            days_left = (premium_until - now).days
            
            if days_left < 0:
                days_text = "⚠️ Muddati tugagan"
            elif days_left == 0:
                days_text = "⚠️ Bugun tugaydi"
            elif days_left <= 7:
                days_text = f"⚠️ {days_left} kun qoldi"
            else:
                days_text = f"✅ {days_left} kun qoldi"
        else:
            date_str = "Abadiy"
            time_str = ""
            days_text = "♾️ Cheksiz"
        
        # Klaviatura - faqat uzaytirish
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Obunani uzaytirish",
                        callback_data="extend_premium"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Tariflar",
                        callback_data="premium_plans"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📞 Qo'llab-quvvatlash",
                        url="https://t.me/SayfullayevBekzod"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Orqaga",
                        callback_data="close_premium"
                    )
                ]
            ]
        )
        
        text = f"""
💎 <b>Premium foydalanuvchi</b>

✅ Sizda Premium obuna mavjud!

📅 <b>Obuna ma'lumotlari:</b>
• Tugash sanasi: <b>{date_str}</b> {time_str}
• Holat: {days_text}

<b>🎁 Sizning imkoniyatlaringiz:</b>
• ♾️ Cheksiz qidiruvlar
• 📊 Cheksiz natijalar
• 📱 Telegram kanallaridan qidirish
• 🔔 Avtomatik bildirishnomalar
• 🚀 Tezroq qidiruv (5 sahifa)
• 🎯 Ustunlik qo'llab-quvvatlanishda
• 📢 Vakansiya e'lon qilish

💡 <b>Obunani uzaytirish:</b>
Obunangizni davom ettirish uchun pastdagi tugmani bosing yoki @SayfullayevBekzod ga murojaat qiling.
"""
        
        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    # FREE foydalanuvchi uchun
    else:
        free_features = PREMIUM_FEATURES['free']
        premium_features = PREMIUM_FEATURES['premium']
        
        text = f"""
💎 <b>Premium Obuna</b>

<b>🆓 Bepul versiya:</b>
• 🔍 {free_features['max_searches_per_day']} ta qidiruv/kun
• 📊 {free_features['max_results']} ta natija
• 🌐 Faqat hh.uz
• ❌ Avtomatik bildirishnomalar yo'q
• ❌ Vakansiya e'lon qila olmaysiz

<b>💎 Premium versiya:</b>
• ♾️ Cheksiz qidiruvlar
• 📊 Cheksiz natijalar
• 📱 Telegram kanallaridan qidirish
• 🔔 Avtomatik bildirishnomalar
• 🚀 Tezroq qidiruv (5 sahifa)
• 🎯 Ustunlik qo'llab-quvvatlanishda
• 📢 Vakansiya e'lon qilish

<b>💰 Narxlar:</b>
📅 1 oy - {PREMIUM_PRICE['monthly']:,} so'm
📆 1 yil - {PREMIUM_PRICE['yearly']:,} so'm (2 oy BEPUL!)

Premium obuna sotib olish uchun pastdagi tugmani bosing!
"""
    
    await message.answer(
        text,
        reply_markup=get_premium_keyboard(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "show_premium")
async def show_premium(callback: CallbackQuery):
    """Premium ma'lumotini ko'rsatish"""
    is_premium = await db.is_premium(callback.from_user.id)
    user = await db.get_user(callback.from_user.id)
    
    if is_premium:
        premium_until = user.get('premium_until')
        if premium_until:
            date_str = premium_until.strftime('%d.%m.%Y')
            time_str = premium_until.strftime('%H:%M')
            
            # Qancha kun qolganini hisoblash
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if premium_until.tzinfo is None:
                premium_until = premium_until.replace(tzinfo=timezone.utc)
            
            days_left = (premium_until - now).days
            
            if days_left < 0:
                days_text = "⚠️ Muddati tugagan"
            elif days_left == 0:
                days_text = "⚠️ Bugun tugaydi"
            elif days_left <= 7:
                days_text = f"⚠️ {days_left} kun qoldi"
            else:
                days_text = f"✅ {days_left} kun qoldi"
        else:
            date_str = "Abadiy"
            time_str = ""
            days_text = "♾️ Cheksiz"
        
        # Klaviatura
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Obunani uzaytirish",
                        callback_data="extend_premium"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Tariflar",
                        callback_data="premium_plans"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📞 Qo'llab-quvvatlash",
                        url="https://t.me/SayfullayevBekzod"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Orqaga",
                        callback_data="close_premium"
                    )
                ]
            ]
        )
        
        text = f"""
💎 <b>Premium foydalanuvchi</b>

✅ Sizda Premium obuna mavjud!

📅 <b>Obuna ma'lumotlari:</b>
• Tugash sanasi: <b>{date_str}</b> {time_str}
• Holat: {days_text}

<b>🎁 Sizning imkoniyatlaringiz:</b>
• ♾️ Cheksiz qidiruvlar
• 📊 Cheksiz natijalar
• 📱 Telegram kanallaridan qidirish
• 🔔 Avtomatik bildirishnomalar
• 🚀 Tezroq qidiruv (5 sahifa)
• 🎯 Ustunlik qo'llab-quvvatlanishda
• 📢 Vakansiya e'lon qilish
"""
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await callback.answer()
        return
    
    # FREE foydalanuvchi uchun
    else:
        free_features = PREMIUM_FEATURES['free']
        
        text = f"""
💎 <b>Premium Obuna</b>

<b>🆓 Bepul versiya:</b>
• 🔍 {free_features['max_searches_per_day']} ta qidiruv/kun
• 📊 {free_features['max_results']} ta natija
• 🌐 Faqat hh.uz
• ❌ Avtomatik bildirishnomalar yo'q

<b>💎 Premium versiya:</b>
• ♾️ Cheksiz qidiruvlar
• 📊 Cheksiz natijalar
• 📱 Telegram kanallaridan qidirish
• 🔔 Avtomatik bildirishnomalar
• 🚀 Tezroq qidiruv
• 🎯 Ustunlik qo'llab-quvvatlanishda
• 📢 Vakansiya e'lon qilish
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_premium_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "extend_premium")
async def extend_premium(callback: CallbackQuery):
    """Premium'ni uzaytirish"""
    await callback.message.edit_text(
        "🔄 <b>Premium obunani uzaytirish</b>\n\n"
        "Obunangizni uzaytirish uchun quyidagi tariflardan birini tanlang:",
        reply_markup=get_plans_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    """Premium sotib olish - avval tekshirish"""
    is_premium = await db.is_premium(callback.from_user.id)
    
    if is_premium:
        # Agar allaqachon Premium bo'lsa
        await callback.answer(
            "✅ Sizda allaqachon Premium mavjud!\n"
            "Obunani uzaytirish uchun '🔄 Obunani uzaytirish' tugmasini bosing.",
            show_alert=True
        )
        return
    
    # FREE foydalanuvchi uchun - tariflar
    await callback.message.edit_text(
        "💰 <b>Premium tariflar</b>\n\n"
        "Quyidagi tariflardan birini tanlang:",
        reply_markup=get_plans_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "premium_plans")
async def show_plans(callback: CallbackQuery):
    """Tariflarni ko'rsatish"""
    await callback.message.edit_text(
        f"💰 <b>Premium tariflar:</b>\n\n"
        f"📅 <b>1 oylik obuna</b>\n"
        f"💵 Narx: {PREMIUM_PRICE['monthly']:,} so'm\n"
        f"📊 1 oy davomida barcha Premium imkoniyatlar\n\n"
        f"📆 <b>1 yillik obuna</b>\n"
        f"💵 Narx: {PREMIUM_PRICE['yearly']:,} so'm\n"
        f"🎁 2 oy BEPUL (10 oy narxida 12 oy!)\n"
        f"📊 1 yil davomida barcha Premium imkoniyatlar\n\n"
        f"💡 <b>Premium imkoniyatlar:</b>\n"
        f"• ♾️ Cheksiz qidiruvlar\n"
        f"• 📊 Cheksiz natijalar\n"
        f"• 📱 Telegram kanallaridan qidirish\n"
        f"• 🔔 Avtomatik bildirishnomalar\n"
        f"• 🚀 5 sahifagacha qidiruv\n"
        f"• 🎯 Ustunlik qo'llab-quvvatlanishda\n"
        f"• 📢 Vakansiya e'lon qilish",
        reply_markup=get_plans_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: CallbackQuery, state: FSMContext):
    """Tarif tanlash"""
    # Premium tekshirish
    is_premium = await db.is_premium(callback.from_user.id)
    user = await db.get_user(callback.from_user.id)
    
    plan = callback.data.replace("plan_", "")
    
    if plan == "monthly":
        price = PREMIUM_PRICE['monthly']
        period = "1 oy"
        days = 30
    else:
        price = PREMIUM_PRICE['yearly']
        period = "1 yil"
        days = 365
    
    # State'ga saqlash
    await state.update_data(
        plan=plan, 
        days=days, 
        price=price, 
        period=period,
        is_extension=is_premium
    )
    
    # Xabar matni
    if is_premium:
        premium_until = user.get('premium_until')
        if premium_until:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            if premium_until.tzinfo is None:
                premium_until = premium_until.replace(tzinfo=timezone.utc)
            
            # Yangi tugash sanasi
            new_expiry = premium_until + timedelta(days=days)
            new_date_str = new_expiry.strftime('%d.%m.%Y')
            
            action_text = "uzaytiriladi"
            extra_info = f"\n\n📅 <b>Yangi tugash sanasi:</b> {new_date_str}"
        else:
            action_text = "uzaytiriladi"
            extra_info = ""
    else:
        action_text = "faollashtiriladi"
        from datetime import datetime, timezone, timedelta
        new_expiry = datetime.now(timezone.utc) + timedelta(days=days)
        new_date_str = new_expiry.strftime('%d.%m.%Y')
        extra_info = f"\n\n📅 <b>Tugash sanasi:</b> {new_date_str}"
    
    await callback.message.edit_text(
        f"💎 <b>Tanlangan tarif: {period}</b>\n\n"
        f"💰 Narx: <b>{price:,} so'm</b>\n"
        f"📅 Davomiyligi: <b>{days} kun</b>{extra_info}\n\n"
        f"📋 <b>To'lov ko'rsatmalari:</b>\n\n"
        f"1️⃣ Quyidagi kartaga to'lov qiling:\n"
        f"💳 <code>8600 1234 5678 9012</code>\n"
        f"👤 Ali Valiyev\n\n"
        f"2️⃣ To'lov chekini skrinshot qiling\n\n"
        f"3️⃣ <b>To'lov chekini shu botga yuboring</b> 📸\n\n"
        f"4️⃣ Biz chekni tekshirib, Premium'ni {action_text}! ✅\n\n"
        f"⚠️ To'lov chekini o'chirmang!\n\n"
        f"💡 To'lov chekini yuborish uchun <b>rasm yuboring</b>",
        parse_mode='HTML'
    )
    
    await state.set_state(PremiumStates.waiting_for_payment_proof)
    await callback.answer()


@router.message(PremiumStates.waiting_for_payment_proof, F.photo)
async def process_payment_proof(message: Message, state: FSMContext):
    """To'lov chekini qabul qilish"""
    data = await state.get_data()
    plan = data.get('plan')
    days = data.get('days')
    price = data.get('price')
    period = data.get('period')
    is_extension = data.get('is_extension', False)
    
    user = message.from_user
    photo = message.photo[-1]  # Eng katta o'lchamdagi rasm
    
    # Foydalanuvchiga javob
    action_text = "uzaytiriladi" if is_extension else "faollashtiriladi"
    
    await message.answer(
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        "📋 Chek adminlarga yuborildi va tekshirilmoqda.\n\n"
        f"⏳ Iltimos, kuting. Tez orada Premium {action_text}!\n\n"
        "📞 Aloqa: @SayfullayevBekzod",
        parse_mode='HTML'
    )
    
    # Premium status tekshirish
    is_premium = await db.is_premium(user.id)
    user_data = await db.get_user(user.id)
    
    if is_premium:
        premium_until = user_data.get('premium_until')
        if premium_until:
            from datetime import timedelta
            if premium_until.tzinfo is None:
                from datetime import timezone
                premium_until = premium_until.replace(tzinfo=timezone.utc)
            
            new_expiry = premium_until + timedelta(days=days)
            current_status = f"📅 Hozirgi tugash: {premium_until.strftime('%d.%m.%Y')}\n📅 Yangi tugash: {new_expiry.strftime('%d.%m.%Y')}"
            action_emoji = "🔄"
            action_word = "UZAYTIRISH"
        else:
            current_status = "📅 Premium: Abadiy"
            action_emoji = "🔄"
            action_word = "UZAYTIRISH"
    else:
        from datetime import datetime, timezone, timedelta
        new_expiry = datetime.now(timezone.utc) + timedelta(days=days)
        current_status = f"📅 Premium beriladi: {new_expiry.strftime('%d.%m.%Y')} gacha"
        action_emoji = "💎"
        action_word = "YANGI OBUNA"
    
    # Adminlarga yuborish
    for admin_id in ADMIN_IDS:
        try:
            # Rasmni yuborish
            caption = f"""
💳 <b>{action_emoji} {action_word} - TO'LOV CHEKI</b>

👤 <b>Foydalanuvchi:</b>
• Ism: {user.first_name} {user.last_name or ''}
• Username: @{user.username or 'N/A'}
• ID: <code>{user.id}</code>

💎 <b>Tarif:</b>
• Reja: {period}
• Narx: {price:,} so'm
• Davomiyligi: {days} kun

📊 <b>Holat:</b>
• Status: {'Premium (uzaytirish)' if is_extension else 'FREE (yangi)'}
{current_status}

📅 <b>Vaqt:</b> {message.date.strftime('%d.%m.%Y %H:%M')}

⬇️ <b>Chekni tekshiring va harakatni tanlang:</b>
"""
            
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=caption,
                reply_markup=get_payment_confirm_keyboard(user.id, days),
                parse_mode='HTML'
            )
            
            logger.info(f"✅ Chek admin {admin_id} ga yuborildi (Extension: {is_extension})")
            
        except Exception as e:
            logger.error(f"❌ Admin {admin_id} ga chek yuborishda xatolik: {e}")
    
    await state.clear()


@router.message(PremiumStates.waiting_for_payment_proof)
async def payment_proof_invalid(message: Message):
    """Noto'g'ri format (rasm emas)"""
    await message.answer(
        "❌ <b>Iltimos, to'lov chekining rasmini yuboring!</b>\n\n"
        "📸 Rasmni telefon gallereyasidan yoki kameradan yuboring.\n\n"
        "Yoki /cancel bekor qilish uchun",
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith("approve_payment_"))
async def approve_payment(callback: CallbackQuery):
    """Admin: To'lovni tasdiqlash"""
    try:
        parts = callback.data.split("_")
        user_id = int(parts[2])
        days = int(parts[3])
        
        # Hozirgi premium statusni tekshirish
        is_premium = await db.is_premium(user_id)
        user = await db.get_user(user_id)
        
        if is_premium:
            premium_until = user.get('premium_until')
            if premium_until:
                from datetime import timezone, timedelta
                if premium_until.tzinfo is None:
                    premium_until = premium_until.replace(tzinfo=timezone.utc)
                
                old_date = premium_until.strftime('%d.%m.%Y')
                
                # Uzaytirish
                new_expiry = premium_until + timedelta(days=days)
                
                action_text = "uzaytirildi"
                status_text = f"📅 Eski: {old_date}\n📅 Yangi: {new_expiry.strftime('%d.%m.%Y')}"
            else:
                old_date = "Abadiy"
                action_text = "uzaytirildi"
                status_text = "Premium uzaytirildi"
        else:
            action_text = "berildi"
            from datetime import datetime, timezone, timedelta
            new_expiry = datetime.now(timezone.utc) + timedelta(days=days)
            status_text = f"📅 Tugash: {new_expiry.strftime('%d.%m.%Y')}"
        
        # Premium berish/uzaytirish
        success = await db.set_premium(user_id, days)
        
        if success:
            # Adminга javob
            await callback.message.edit_caption(
                caption=callback.message.caption + f"\n\n✅ <b>TASDIQLANDI!</b>\n"
                f"💎 Premium {days} kunga {action_text}.\n{status_text}",
                parse_mode='HTML'
            )
            
            # Foydalanuvchiga xabar
            try:
                user = await db.get_user(user_id)
                premium_until = user.get('premium_until')
                date_str = premium_until.strftime('%d.%m.%Y') if premium_until else 'Abadiy'
                
                await callback.bot.send_message(
                    user_id,
                    f"🎉🎉🎉 <b>TABRIKLAYMIZ!</b>\n\n"
                    f"✅ To'lovingiz tasdiqlandi!\n\n"
                    f"💎 Premium obuna {action_text}!\n"
                    f"📅 Amal qilish muddati: {date_str} gacha\n\n"
                    f"<b>🎁 Sizning imkoniyatlaringiz:</b>\n"
                    f"• ♾️ Cheksiz qidiruvlar\n"
                    f"• 📱 Telegram kanallaridan qidirish\n"
                    f"• 🔔 Avtomatik bildirishnomalar\n"
                    f"• 📢 Vakansiya e'lon qilish\n"
                    f"• 🚀 Tezroq qidiruv\n\n"
                    f"🚀 Botdan foydalanishni davom eting!",
                    parse_mode='HTML'
                )
                
                logger.info(f"✅ User {user_id} premium {action_text}: {days} kun")
                
            except Exception as e:
                logger.error(f"❌ User {user_id} ga xabar yuborishda xatolik: {e}")
            
            await callback.answer("✅ Premium berildi!", show_alert=True)
        else:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ approve_payment xatolik: {e}", exc_info=True)
        await callback.answer("❌ Xatolik!", show_alert=True)


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment(callback: CallbackQuery):
    """Admin: To'lovni bekor qilish"""
    try:
        parts = callback.data.split("_")
        user_id = int(parts[2])
        days = int(parts[3])
        
        # Adminга javob
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n❌ <b>BEKOR QILINDI!</b>",
            parse_mode='HTML'
        )
        
        # Foydalanuvchiga xabar
        try:
            await callback.bot.send_message(
                user_id,
                "❌ <b>To'lov rad etildi</b>\n\n"
                "To'lov chekingiz tasdiqlanmadi.\n\n"
                "Sabablari:\n"
                "• Chek aniq emas\n"
                "• To'lov summasi noto'g'ri\n"
                "• Boshqa muammo\n\n"
                "📞 Aloqa uchun: @SayfullayevBekzod",
                parse_mode='HTML'
            )
            
            logger.info(f"❌ User {user_id} to'lovi rad etildi")
            
        except Exception as e:
            logger.error(f"❌ User {user_id} ga xabar yuborishda xatolik: {e}")
        
        await callback.answer("❌ To'lov rad etildi", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ reject_payment xatolik: {e}", exc_info=True)
        await callback.answer("❌ Xatolik!", show_alert=True)


@router.callback_query(F.data == "close_premium")
async def close_premium(callback: CallbackQuery):
    """Premium oynasini yopish"""
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "/cancel")
async def cancel_payment(message: Message, state: FSMContext):
    """To'lovni bekor qilish"""
    current_state = await state.get_state()
    
    if current_state == PremiumStates.waiting_for_payment_proof:
        await state.clear()
        await message.answer(
            "❌ To'lov jarayoni bekor qilindi.\n\n"
            "Qaytadan boshlash uchun 💎 Premium tugmasini bosing.",
            parse_mode='HTML'
        )
    else:
        await message.answer("Hozir hech narsa bekor qilinmaydi.")
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from database import db
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
router = Router()


# Referral mukofotlar
REFERRAL_REWARDS = {
    '1': {'days': 1, 'title': '1 ta do\'st'},
    '3': {'days': 7, 'title': '3 ta do\'st'},
    '5': {'days': 14, 'title': '5 ta do\'st'},
    '10': {'days': 30, 'title': '10 ta do\'st'},
}


def get_referral_keyboard(user_id: int):
    """Referral klaviaturasi"""
    ref_link = f"https://t.me/vacancyuzbekbot?start=ref_{user_id}"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Ulashish",
                    url=f"https://t.me/share/url?url={ref_link}&text=Ish topish uchun zo'r bot! 🚀"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistikam",
                    callback_data="referral_stats"
                ),
                InlineKeyboardButton(
                    text="🎁 Mukofotlar",
                    callback_data="referral_rewards"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="close_referral"
                )
            ]
        ]
    )


@router.message(F.text == "🤝 Taklif qilish")
async def cmd_referral(message: Message):
    """Referral sistema"""
    user_id = message.from_user.id
    
    # Referral statistika
    async with db.pool.acquire() as conn:
        # Referral count
        referrals = await conn.fetch('''
            SELECT user_id, first_name, created_at, premium_until
            FROM users
            WHERE referred_by = $1
            ORDER BY created_at DESC
        ''', user_id)
        
        ref_count = len(referrals)
        
        # Premium referrals
        premium_refs = sum(1 for r in referrals if r['premium_until'] and r['premium_until'] > datetime.now(timezone.utc))
    
    # Referral link
    ref_link = f"https://t.me/vacancyuzbekbot?start=ref_{user_id}"
    
    # Keyingi mukofot
    next_reward = None
    for count, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0])):
        if ref_count < int(count):
            next_reward = (int(count), reward)
            break
    
    text = "🤝 <b>Do'stlarni taklif qilish</b>\n\n"
    text += f"👥 <b>Sizning referrallaringiz:</b> {ref_count} ta\n"
    if premium_refs > 0:
        text += f"💎 Premium: {premium_refs} ta\n"
    text += "\n"
    
    # Mukofotlar
    text += "🎁 <b>Mukofotlar:</b>\n\n"
    
    for count, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0])):
        if ref_count >= int(count):
            text += f"✅ {reward['title']}: +{reward['days']} kun Premium\n"
        elif next_reward and int(count) == next_reward[0]:
            remaining = int(count) - ref_count
            text += f"⏳ {reward['title']}: +{reward['days']} kun (yana {remaining} ta kerak)\n"
        else:
            text += f"🔒 {reward['title']}: +{reward['days']} kun Premium\n"
    
    text += f"\n🔗 <b>Sizning linkingiz:</b>\n"
    text += f"<code>{ref_link}</code>\n\n"
    text += "💡 Do'stlaringizga ulashing va Premium mukofot oling!"
    
    await message.answer(
        text,
        reply_markup=get_referral_keyboard(user_id),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "referral_stats")
async def referral_stats(callback: CallbackQuery):
    """Referral statistika"""
    user_id = callback.from_user.id
    
    async with db.pool.acquire() as conn:
        referrals = await conn.fetch('''
            SELECT 
                user_id,
                first_name,
                username,
                created_at,
                premium_until,
                (premium_until > NOW()) as is_premium
            FROM users
            WHERE referred_by = $1
            ORDER BY created_at DESC
            LIMIT 20
        ''', user_id)
    
    if not referrals:
        text = "📊 <b>Statistika</b>\n\n"
        text += "Sizda hali referrallar yo'q.\n\n"
        text += "💡 Do'stlaringizni taklif qiling va Premium mukofot oling!"
    else:
        text = f"📊 <b>Referral statistika</b>\n\n"
        text += f"👥 Jami: <b>{len(referrals)}</b> ta\n\n"
        text += "Oxirgi 20 ta:\n\n"
        
        for i, ref in enumerate(referrals[:10], 1):
            name = ref['first_name']
            username = f"@{ref['username']}" if ref['username'] else ""
            date = ref['created_at'].strftime('%d.%m.%Y')
            status = "💎" if ref['is_premium'] else "🆓"
            
            text += f"{i}. {status} {name} {username}\n"
            text += f"   📅 {date}\n\n"
        
        if len(referrals) > 10:
            text += f"... va yana {len(referrals) - 10} ta"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_referral")]
            ]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "referral_rewards")
async def referral_rewards(callback: CallbackQuery):
    """Mukofotlar ro'yxati"""
    user_id = callback.from_user.id
    
    async with db.pool.acquire() as conn:
        ref_count = await conn.fetchval('''
            SELECT COUNT(*) FROM users
            WHERE referred_by = $1
        ''', user_id)
    
    text = "🎁 <b>Referral mukofotlari</b>\n\n"
    text += f"👥 Sizning referrallaringiz: <b>{ref_count}</b> ta\n\n"
    
    for count, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0])):
        if ref_count >= int(count):
            text += f"✅ <b>{reward['title']}</b>\n"
            text += f"   Mukofot: +{reward['days']} kun Premium\n"
            text += f"   Status: Olindi ✅\n\n"
        else:
            remaining = int(count) - ref_count
            text += f"🔒 <b>{reward['title']}</b>\n"
            text += f"   Mukofot: +{reward['days']} kun Premium\n"
            text += f"   Kerak: yana {remaining} ta\n\n"
    
    text += "💡 Har bir yangi referral uchun avtomatik mukofot beriladi!"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_referral")]
            ]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "show_referral")
async def show_referral(callback: CallbackQuery):
    """Referral sahifasini ko'rsatish"""
    user_id = callback.from_user.id
    
    async with db.pool.acquire() as conn:
        referrals = await conn.fetch('''
            SELECT user_id FROM users
            WHERE referred_by = $1
        ''', user_id)
        
        ref_count = len(referrals)
    
    ref_link = f"https://t.me/vacancyuzbekbot?start=ref_{user_id}"
    
    text = "🤝 <b>Do'stlarni taklif qilish</b>\n\n"
    text += f"👥 <b>Sizning referrallaringiz:</b> {ref_count} ta\n\n"
    
    text += "🎁 <b>Mukofotlar:</b>\n"
    for count, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0]))[:3]:
        status = "✅" if ref_count >= int(count) else "🔒"
        text += f"{status} {reward['title']}: +{reward['days']} kun\n"
    
    text += f"\n🔗 <b>Sizning linkingiz:</b>\n"
    text += f"<code>{ref_link}</code>\n\n"
    text += "💡 Do'stlaringizga ulashing!"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_referral_keyboard(user_id),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "close_referral")
async def close_referral(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()


# Referral link orqali start
async def process_referral_start(message: Message, referrer_id: int):
    """Referral link orqali kelgan foydalanuvchi"""
    user_id = message.from_user.id
    
    # O'ziga o'zi referral bo'lolmaydi
    if user_id == referrer_id:
        logger.info(f"[REFERRAL] User {user_id} tried to refer themselves")
        return
    
    # Allaqachon registered bo'lsa
    user = await db.get_user(user_id)
    if user and user.get('referred_by'):
        logger.info(f"[REFERRAL] User {user_id} already has referrer: {user.get('referred_by')}")
        return
    
    # Referrerni saqlash
    async with db.pool.acquire() as conn:
        await conn.execute('''
            UPDATE users
            SET referred_by = $2
            WHERE user_id = $1
        ''', user_id, referrer_id)
        
        # Referral count
        ref_count = await conn.fetchval('''
            SELECT COUNT(*) FROM users
            WHERE referred_by = $1
        ''', referrer_id)
    
    logger.info(f"[REFERRAL] New referral: user {user_id} by referrer {referrer_id}. Total: {ref_count}")
    
    # Referrerga xabar
    try:
        await message.bot.send_message(
            referrer_id,
            f"🎉 <b>Yangi referral!</b>\n\n"
            f"👤 {message.from_user.first_name} sizning linkingiz orqali botga qo'shildi!\n\n"
            f"👥 Jami referrallaringiz: {ref_count} ta\n\n"
            f"💡 Mukofotlarni olish uchun: 🤝 Taklif qilish",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"[REFERRAL] Error sending referral notification: {e}")
    
    # Mukofot tekshirish va berish
    for count_str, reward in REFERRAL_REWARDS.items():
        count = int(count_str)
        if ref_count == count:
            # Mukofot berish
            days = reward['days']
            
            logger.info(f"[REFERRAL] Giving {days} days premium to referrer {referrer_id}")
            
            # Premium berish
            success = await db.set_premium(referrer_id, days)
            
            if success:
                logger.info(f"[REFERRAL] ✅ Premium given successfully to {referrer_id}!")
                
                try:
                    await message.bot.send_message(
                        referrer_id,
                        f"🎁🎁🎁 <b>MUKOFOT!</b>\n\n"
                        f"Tabriklaymiz! {reward['title']} mukofoti:\n"
                        f"💎 +{days} kun Premium!\n\n"
                        f"Premium faollashtirildi! 🚀\n\n"
                        f"Tekshirish: 💎 Premium bo'limiga o'ting",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"[REFERRAL] Error sending reward message: {e}")
            else:
                logger.error(f"[REFERRAL] ❌ Failed to give premium to {referrer_id}!")
            
            break
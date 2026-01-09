from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from database import db
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
router = Router()


# Referral mukofotlar
# Referral mukofotlar - YANGILANGAN (5, 10, 20, 30)
REFERRAL_REWARDS = {
    '5': {'days': 3, 'title': '5 ta do\'st'},
    '10': {'days': 6, 'title': '10 ta do\'st'},
    '20': {'days': 12, 'title': '20 ta do\'st'},
    '30': {'days': 30, 'title': '30 ta do\'st'},
}


async def get_referral_keyboard(user_id: int, bot: Bot):
    """Referral klaviaturasi"""
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user_id}"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Ulashish",
                    url=f"https://t.me/share/url?url={ref_link}&text=Ish topish uchun zo'r bot! 🚀"
                )
            ],
            [
                InlineKeyboardButton(text="📊 Statistikam", callback_data="referral_stats"),
                InlineKeyboardButton(text="🏆 Leaderboard", callback_data="referral_leaderboard")
            ],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="close_referral")]
        ]
    )


@router.message(F.text == "🤝 Taklif qilish")
async def cmd_referral(message: Message):
    """Referral sistema"""
    user_id = message.from_user.id
    
    # Referral statistika
    stats = await db.get_referral_stats(user_id)
    ref_count = stats['total']
    premium_refs = stats['premium']
    
    me = await message.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user_id}"
    
    text = "🤝 <b>Do'stlarni taklif qilish</b>\n\n"
    text += "Do'stlarni taklif qiling va Premium bonus oling:\n"
    text += "• 5 ta do'st = 3 kun\n"
    text += "• 10 ta do'st = 6 kun\n"
    text += "• 20 ta do'st = 12 kun\n"
    text += "• 30 ta do'st = 30 kun!\n\n"
    
    text += f"👥 <b>Sizning referrallaringiz:</b> {ref_count} ta\n"
    if premium_refs > 0:
        text += f"💎 Premium referrallar: {premium_refs} ta\n"
    
    text += "\n🎁 <b>Mukofotlar:</b>\n"
    for count_str, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0])):
        count = int(count_str)
        if ref_count >= count:
            status = "✅"
        elif ref_count >= count - 2:
            status = "⏳"
        else:
            status = "🔒"
        
        text += f"{status} {reward['title']}: +{reward['days']} kun Premium\n"
        if status == "⏳":
            text += f"   (yana {count - ref_count} ta kerak)\n"
    
    text += f"\n🔗 <b>Sizning linkingiz:</b>\n<code>{ref_link}</code>\n\n"
    text += "💡 Do'stlaringizga ulashing va avtomatik Premium bonus oling!"
    
    await message.answer(
        text,
        reply_markup=await get_referral_keyboard(user_id, message.bot),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "referral_stats")
async def referral_stats(callback: CallbackQuery):
    """Referral statistika"""
    user_id = callback.from_user.id
    referrals = await db.get_referral_list(user_id, limit=20)
    
    if not referrals:
        text = "📊 <b>Statistika</b>\n\nSizda hali referrallar yo'q.\n\n"
        text += "💡 Do'stlaringizni taklif qiling va Premium mukofot oling!"
    else:
        text = f"📊 <b>Referral statistika</b> (oxirgi 20 ta)\n\n"
        for i, ref in enumerate(referrals, 1):
            name = ref['first_name']
            username = f" @{ref['username']}" if ref['username'] else ""
            date = ref['created_at'].strftime('%d.%m.%Y')
            status = "💎" if ref['is_premium'] else "🆓"
            text += f"{i}. {status} {name}{username} - {date}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_referral")]]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "referral_leaderboard")
async def referral_leaderboard(callback: CallbackQuery):
    """Top referrallar"""
    top = await db.get_top_referrers(10)
    
    text = "🏆 <b>Referral Leaderboard</b>\n\n"
    if not top:
        text += "Hali natijalar yo'q."
    else:
        for i, user in enumerate(top, 1):
            emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "👤"))
            text += f"{emoji} {i}. {user['first_name']} - <b>{user['total']}</b> ta\n"
    
    text += "\n💡 Do'stlarni taklif qiling va ro'yxatga kiring!"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_referral")]
        ]),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "referral_rewards")
async def referral_rewards(callback: CallbackQuery):
    """Mukofotlar ro'yxati"""
    user_id = callback.from_user.id
    stats = await db.get_referral_stats(user_id)
    ref_count = stats['total']
    
    text = "🎁 <b>Referral mukofotlari</b>\n\n"
    for count_str, reward in sorted(REFERRAL_REWARDS.items(), key=lambda x: int(x[0])):
        count = int(count_str)
        if ref_count >= count:
            text += f"✅ <b>{reward['title']}</b> - Olindi!\n"
        else:
            text += f"🔒 <b>{reward['title']}</b> - Yana {count - ref_count} ta kerak\n"
        text += f"   +{reward['days']} kun Premium\n\n"
    
    text += "💡 Har bir yangi referral uchun mukofot avtomatik beriladi!"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_referral")]]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "show_referral")
async def show_referral(callback: CallbackQuery):
    """Referral sahifasini qayta ko'rsatish"""
    # Call original message handler logic
    await cmd_referral(callback.message)
    await callback.message.delete()
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
    if user_id == referrer_id: return
    
    # Allaqachon registered bo'lsa tekshirish (db.add_user allaqachon chaqirilgan bo'lishi kerak)
    user = await db.get_user(user_id)
    if user and user.get('referred_by'): return
    
    # Referrerni saqlash
    async with db.pool.acquire() as conn:
        await conn.execute('UPDATE users SET referred_by = $2 WHERE user_id = $1', user_id, referrer_id)
        # Yangi count
        ref_count = await conn.fetchval('SELECT COUNT(*) FROM users WHERE referred_by = $1', referrer_id)
    
    # Referrerga xabar
    try:
        await message.bot.send_message(
            referrer_id,
            f"🎉 <b>Yangi referral!</b>\n\n"
            f"👤 {message.from_user.first_name} taklifnomangiz orqali qo'shildi!\n"
            f"👥 Jami: {ref_count} ta\n"
            f"💡 Mukofotlarni tekshirish: 🤝 Taklif qilish",
            parse_mode='HTML'
        )
    except: pass
    
    # Mukofot tekshirish
    for count_str, reward in REFERRAL_REWARDS.items():
        if ref_count == int(count_str):
            days = reward['days']
            if await db.set_premium(referrer_id, days):
                try:
                    await message.bot.send_message(
                        referrer_id,
                        f"🎁 <b>YANGI MUKOFOT!</b>\n\n"
                        f"{reward['title']} uchun sizga 💎 <b>+{days} kun Premium</b> berildi!\n\n"
                        f"Faol foydalanishda davom eting! 🚀",
                        parse_mode='HTML'
                    )
                except: pass
            break
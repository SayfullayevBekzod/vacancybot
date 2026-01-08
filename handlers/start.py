from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from database import db
import logging

logger = logging.getLogger(__name__)

router = Router()

async def get_main_keyboard(user_id: int):
    """Asosiy klaviatura - Premium va funksiyalarga qarab"""
    is_premium = await db.is_premium(user_id)
    
    keyboard_buttons = [
        [
            KeyboardButton(text="🔍 Vakansiya qidirish"),
            KeyboardButton(text="⚙️ Sozlamalar")
        ],
        [
            KeyboardButton(text="💎 Premium"),
            KeyboardButton(text="💾 Saqlangan")
        ]
    ]
    
    # Premium foydalanuvchilar uchun qo'shimcha funksiyalar
    if is_premium:
        keyboard_buttons.insert(2, [
            KeyboardButton(text="📢 Vakansiya qo'shish"),
            KeyboardButton(text="🎯 Smart tavsiya")
        ])
        keyboard_buttons.insert(3, [
            KeyboardButton(text="🔔 Bildirishnomalar"),
            KeyboardButton(text="📊 Statistika")
        ])
    else:
        keyboard_buttons.insert(2, [
            KeyboardButton(text="📊 Statistika")
        ])
    
    # Referral barcha uchun
    keyboard_buttons.append([
        KeyboardButton(text="🤝 Taklif qilish"),
        KeyboardButton(text="ℹ️ Yordam")
    ])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )
    return keyboard


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start komandasi"""
    user = message.from_user
    
    # Referral tekshirish
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        args = message.text.split()[1]
        if args.startswith('ref_'):
            try:
                referrer_id = int(args.replace('ref_', ''))
            except:
                pass
    
    # Foydalanuvchini bazaga qo'shish
    await db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Referral processing
    if referrer_id:
        from handlers.referral import process_referral_start
        await process_referral_start(message, referrer_id)
    
    logger.info(f"User start: {user.id} - {user.username} (Ref: {referrer_id})")
    
    # Premium status
    is_premium = await db.is_premium(user.id)
    premium_badge = "💎" if is_premium else ""
    
    welcome_text = f"""
👋 Assalomu alaykum, <b>{user.first_name}</b> {premium_badge}!

🤖 Men <b>Vacancy Bot</b>man. 

🎯 <b>Men nima qila olaman?</b>
• hh.uz dan vakansiyalarni avtomatik yig'aman
• Telegram kanallaridan vakansiya topaman (Premium)
• Sizning talablaringizga mos vakansiyalarni filtrlayman
• Har kuni yangi vakansiyalar haqida xabar beraman
"""

    if is_premium:
        welcome_text += """
• 📢 Vakansiya e'lon qilishingiz mumkin
• 🎯 AI tavsiyalar (Smart Matching)
• 🔔 Push bildirishnomalar

💎 <b>Siz Premium foydalanuvchisiz!</b>
"""
    else:
        welcome_text += """

🆓 <b>Free versiya:</b>
• 5 ta qidiruv/kun
• 10 ta natija
• Faqat hh.uz

💡 Premium'ga o'tib, barcha imkoniyatlardan foydalaning!
"""
    
    welcome_text += """
⚙️ <b>Boshlash uchun:</b>
1. "Sozlamalar" tugmasini bosing
2. O'zingizga mos filtrlarni o'rnating
3. Men sizga mos vakansiyalarni yuboraman!

📱 <b>Asosiy funksiyalar:</b>
• 🔍 Vakansiya qidirish - hozir qidirish
• 💾 Saqlangan - yoqqan vakansiyalar
• 🤝 Taklif qilish - do'stlar va bonus
"""

    if is_premium:
        welcome_text += "• 🎯 Smart tavsiya - AI tavsiyalar\n"
        welcome_text += "• 🔔 Bildirishnomalar - real-time xabarlar\n"
    
    welcome_text += "• ℹ️ Yordam - qo'llanma\n\nKeling, boshlaymiz! 🚀"
    
    await message.answer(
        welcome_text,
        reply_markup=await get_main_keyboard(user.id),
        parse_mode='HTML'
    )


@router.message(F.text == "ℹ️ Yordam")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam komandasi"""
    is_premium = await db.is_premium(message.from_user.id)
    
    help_text = """
📖 <b>Yordam</b>

<b>🔍 Vakansiya qidirish</b>
Joriy vakansiyalarni qidirish va ko'rish.

<b>⚙️ Sozlamalar</b>
Filtrlarni sozlash:
• 🔑 Kalit so'zlar
• 📍 Joylashuv
• 💰 Maosh
• 👔 Tajriba
• 🌐 Manbalar

<b>💾 Saqlangan</b>
Yoqqan vakansiyalarni saqlash va keyinchalik ko'rish.

<b>🤝 Taklif qilish</b>
Do'stlarni taklif qiling va Premium bonus oling:
• 5 ta do'st = 3 kun
• 10 ta do'st = 6 kun
• 20 ta do'st = 12 kun
• 10 ta do'st = 30 kun!

<b>📊 Statistika</b>
• Vakansiya statistikasi
• Bozor tahlili
• Sizning faoliyatingiz
"""

    if is_premium:
        help_text += """
<b>💎 Premium funksiyalar:</b>

<b>📢 Vakansiya qo'shish</b>
O'z vakansiyangizni botga joylashtiring.

<b>🎯 Smart tavsiya</b>
AI sizga eng mos vakansiyalarni topadi:
• Match % ko'rsatiladi
• Avtomatik saralash
• Personallashtirilgan tavsiyalar

<b>🔔 Bildirishnomalar</b>
Real-time xabarlar:
• Yangi vakansiya chiqqanda darhol
• Kunlik xulosa
• Spam yo'q
"""
    else:
        help_text += """
<b>💎 Premium bilan:</b>
• 📢 Vakansiya e'lon qilish
• 🎯 AI tavsiyalar
• 🔔 Real-time bildirishnomalar
• 📱 Telegram kanallar
• ♾️ Cheksiz qidiruvlar
"""
    
    help_text += """
<b>❓ Savollar</b>
@SayfullayevBekzod ga murojaat qiling.
"""
    
    await message.answer(help_text, parse_mode='HTML')


@router.message(F.text == "📊 Statistika")
async def cmd_stats(message: Message):
    """Statistika"""
    # Analytics handler'ga yo'naltirish
    from handlers.analytics import cmd_analytics
    await cmd_analytics(message)
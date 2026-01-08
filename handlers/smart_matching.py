from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from filters import vacancy_filter
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
router = Router()


def calculate_match_score(vacancy: dict, user_profile: dict) -> int:
    """Vakansiya va foydalanuvchi o'rtasidagi match %"""
    score = 0
    max_score = 100
    
    # Keywords match (40%)
    user_keywords = user_profile.get('keywords', [])
    if user_keywords:
        vac_text = f"{vacancy.get('title', '')} {vacancy.get('description', '')}".lower()
        matched_keywords = sum(1 for kw in user_keywords if kw.lower() in vac_text)
        score += int((matched_keywords / len(user_keywords)) * 40)
    else:
        score += 20  # Default if no keywords
    
    # Location match (20%)
    user_locations = user_profile.get('locations', [])
    vac_location = vacancy.get('location', '').lower()
    if user_locations:
        location_match = any(loc.lower() in vac_location for loc in user_locations)
        if location_match:
            score += 20
    else:
        score += 10
    
    # Salary match (20%)
    user_salary_min = user_profile.get('salary_min')
    vac_salary_min = vacancy.get('salary_min')
    vac_salary_max = vacancy.get('salary_max')
    
    if user_salary_min and (vac_salary_min or vac_salary_max):
        if vac_salary_max and vac_salary_max >= user_salary_min:
            score += 20
        elif vac_salary_min and vac_salary_min >= user_salary_min * 0.8:
            score += 15
    else:
        score += 10
    
    # Experience match (20%)
    user_exp = user_profile.get('experience_level')
    vac_exp = vacancy.get('experience_level')
    
    if user_exp and vac_exp:
        if user_exp == vac_exp:
            score += 20
        elif user_exp in ['between_1_and_3', 'between_3_and_6'] and vac_exp == 'not_specified':
            score += 15
    else:
        score += 10
    
    return min(score, max_score)


def get_match_emoji(score: int) -> str:
    """Match %ga qarab emoji"""
    if score >= 90:
        return "🔥"
    elif score >= 75:
        return "⭐️"
    elif score >= 60:
        return "✨"
    elif score >= 50:
        return "💫"
    else:
        return "📌"


def get_smart_keyboard():
    """Smart matching klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Eng mos vakansiyalar", callback_data="smart_best_match"),
                InlineKeyboardButton(text="🔥 Top 10", callback_data="smart_top_10")
            ],
            [
                InlineKeyboardButton(text="📊 Profilim", callback_data="smart_profile"),
                InlineKeyboardButton(text="⚙️ Sozlash", callback_data="smart_settings")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="close_smart")
            ]
        ]
    )


@router.message(F.text == "🎯 Smart tavsiya")
async def cmd_smart_matching(message: Message):
    """Smart matching asosiy sahifa"""
    # Premium tekshirish
    is_premium = await db.is_premium(message.from_user.id)
    
    if not is_premium:
        await message.answer(
            "🔒 <b>Premium xususiyat!</b>\n\n"
            "Smart Matching - AI tavsiyalar faqat Premium foydalanuvchilar uchun.\n\n"
            "💎 Premium bilan:\n"
            "• AI sizga eng mos vakansiyalarni topadi\n"
            "• Match % ko'rsatiladi\n"
            "• Avtomatik saralash\n"
            "• Personallashtirilgan tavsiyalar\n\n"
            "Premium sotib olish uchun 💎 Premium tugmasini bosing.",
            parse_mode='HTML'
        )
        return
    
    # User profili
    user_filter = await db.get_user_filter(message.from_user.id)
    
    if not user_filter or not user_filter.get('keywords'):
        await message.answer(
            "⚠️ <b>Avval profilingizni to'ldiring!</b>\n\n"
            "Smart Matching ishlashi uchun:\n"
            "1. ⚙️ Sozlamalar\n"
            "2. Kalit so'zlar, joylashuv va boshqalarni to'ldiring\n"
            "3. Qaytadan urinib ko'ring\n\n"
            "💡 Qanchalik to'liq bo'lsa, shunchalik aniq tavsiyalar!",
            parse_mode='HTML'
        )
        return
    
    # Profile completeness
    completeness = 0
    if user_filter.get('keywords'):
        completeness += 30
    if user_filter.get('locations'):
        completeness += 20
    if user_filter.get('salary_min'):
        completeness += 20
    if user_filter.get('experience_level'):
        completeness += 30
    
    text = "🎯 <b>Smart Matching</b>\n"
    text += "<i>AI powered vakansiya tavsiyalari</i>\n\n"
    
    text += f"📊 <b>Profil to'liqlik:</b> {completeness}%\n"
    if completeness < 100:
        text += "💡 Profilni to'ldirib, yaxshiroq natijalar oling!\n"
    text += "\n"
    
    text += "<b>🎯 Nima qiladi?</b>\n"
    text += "• Sizning profilingizga qarab eng mos vakansiyalarni topadi\n"
    text += "• Har bir vakansiya uchun match % hisoblanadi\n"
    text += "• Eng yuqori match'larni birinchi ko'rsatadi\n\n"
    
    text += "Tanlang:"
    
    await message.answer(
        text,
        reply_markup=get_smart_keyboard(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "smart_best_match")
async def smart_best_match(callback: CallbackQuery):
    """Eng mos vakansiyalar"""
    await callback.message.edit_text(
        "🔍 <b>Sizga eng mos vakansiyalarni qidiryapman...</b>\n\n"
        "⏳ Bu biroz vaqt olishi mumkin...",
        parse_mode='HTML'
    )
    
    try:
        # User profili
        user_filter = await db.get_user_filter(callback.from_user.id)
        
        # Vakansiyalarni olish (oxirgi 7 kun)
        async with db.pool.acquire() as conn:
            vacancies = await conn.fetch('''
                SELECT * FROM vacancies
                WHERE published_date > NOW() - INTERVAL '7 days'
                ORDER BY published_date DESC
                LIMIT 100
            ''')
        
        if not vacancies:
            await callback.message.edit_text(
                "😕 <b>Hech qanday vakansiya topilmadi</b>\n\n"
                "Keyinroq qayta urinib ko'ring.",
                parse_mode='HTML'
            )
            return
        
        # Match score hisoblash
        scored_vacancies = []
        for vac in vacancies:
            vac_dict = dict(vac)
            score = calculate_match_score(vac_dict, user_filter)
            vac_dict['match_score'] = score
            scored_vacancies.append(vac_dict)
        
        # Saralash (yuqoridan pastga)
        scored_vacancies.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Top 5 ni ko'rsatish
        text = "🎯 <b>Sizga eng mos vakansiyalar</b>\n\n"
        
        for i, vac in enumerate(scored_vacancies[:5], 1):
            score = vac['match_score']
            emoji = get_match_emoji(score)
            
            text += f"{i}. {emoji} <b>{vac['title']}</b>\n"
            text += f"   Match: <b>{score}%</b>\n"
            text += f"   🏢 {vac['company']}\n"
            text += f"   📍 {vac['location']}\n"
            
            if vac['salary_min'] or vac['salary_max']:
                salary = ""
                if vac['salary_min']:
                    salary = f"{vac['salary_min']:,}"
                if vac['salary_max']:
                    salary += f" - {vac['salary_max']:,}"
                text += f"   💰 {salary} so'm\n"
            
            text += f"   🔗 {vac['url']}\n\n"
        
        text += "💡 Match % qanchalik yuqori bo'lsa, sizga shunchalik mos!"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Top 10", callback_data="smart_top_10")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_smart")]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Smart matching error: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Xatolik yuz berdi</b>\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring.",
            parse_mode='HTML'
        )
    
    await callback.answer()


@router.callback_query(F.data == "smart_top_10")
async def smart_top_10(callback: CallbackQuery):
    """Top 10 vakansiyalar (qisqacha)"""
    try:
        user_filter = await db.get_user_filter(callback.from_user.id)
        
        async with db.pool.acquire() as conn:
            vacancies = await conn.fetch('''
                SELECT * FROM vacancies
                WHERE published_date > NOW() - INTERVAL '7 days'
                ORDER BY published_date DESC
                LIMIT 100
            ''')
        
        # Scoring
        scored_vacancies = []
        for vac in vacancies:
            vac_dict = dict(vac)
            score = calculate_match_score(vac_dict, user_filter)
            vac_dict['match_score'] = score
            scored_vacancies.append(vac_dict)
        
        scored_vacancies.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Top 10
        text = "🔥 <b>Top 10 vakansiyalar</b>\n"
        text += "<i>Sizga eng mos</i>\n\n"
        
        for i, vac in enumerate(scored_vacancies[:10], 1):
            score = vac['match_score']
            emoji = get_match_emoji(score)
            
            text += f"{i}. {emoji} <b>{score}%</b> - {vac['title'][:40]}\n"
            text += f"   🏢 {vac['company'][:30]}\n\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Batafsil", callback_data="smart_best_match")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_smart")]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Top 10 error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "smart_profile")
async def smart_profile(callback: CallbackQuery):
    """Foydalanuvchi profili"""
    user_filter = await db.get_user_filter(callback.from_user.id)
    
    if not user_filter:
        await callback.message.edit_text(
            "⚠️ Profil to'ldirilmagan\n\n"
            "⚙️ Sozlamalar bo'limiga o'ting",
            parse_mode='HTML'
        )
        return
    
    # Profile analysis
    completeness = 0
    missing = []
    
    if user_filter.get('keywords'):
        completeness += 30
    else:
        missing.append("🔑 Kalit so'zlar")
    
    if user_filter.get('locations'):
        completeness += 20
    else:
        missing.append("📍 Joylashuv")
    
    if user_filter.get('salary_min'):
        completeness += 20
    else:
        missing.append("💰 Maosh")
    
    if user_filter.get('experience_level'):
        completeness += 30
    else:
        missing.append("👔 Tajriba")
    
    text = f"📊 <b>Sizning profilingiz</b>\n\n"
    text += f"To'liqlik: <b>{completeness}%</b>\n\n"
    
    if completeness == 100:
        text += "✅ Profil to'liq to'ldirilgan!\n"
        text += "🎯 Smart Matching eng yaxshi ishlaydi!\n\n"
    else:
        text += "⚠️ Profilni to'ldiring:\n"
        for item in missing:
            text += f"  • {item}\n"
        text += "\n💡 To'liq profil = yaxshiroq tavsiyalar!\n\n"
    
    # Current settings
    text += "<b>Hozirgi sozlamalar:</b>\n"
    if user_filter.get('keywords'):
        text += f"🔑 {', '.join(user_filter['keywords'][:3])}\n"
    if user_filter.get('locations'):
        text += f"📍 {', '.join(user_filter['locations'])}\n"
    if user_filter.get('salary_min'):
        text += f"💰 dan {user_filter['salary_min']:,} so'm\n"
    if user_filter.get('experience_level'):
        exp_map = {
            'no_experience': 'Tajribasiz',
            'between_1_and_3': '1-3 yil',
            'between_3_and_6': '3-6 yil',
            'more_than_6': '6+ yil'
        }
        text += f"👔 {exp_map.get(user_filter['experience_level'], 'N/A')}\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ O'zgartirish", callback_data="smart_settings")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_smart")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "smart_settings")
async def smart_settings(callback: CallbackQuery):
    """Sozlamalar"""
    await callback.message.edit_text(
        "⚙️ <b>Profilni sozlash</b>\n\n"
        "Smart Matching uchun profilingizni to'ldiring:\n\n"
        "1. Asosiy menyu\n"
        "2. ⚙️ Sozlamalar\n"
        "3. Barcha maydonlarni to'ldiring\n\n"
        "💡 To'liq profil = aniq tavsiyalar!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_smart")]
            ]
        ),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "show_smart")
async def show_smart(callback: CallbackQuery):
    """Smart matching sahifasi"""
    await cmd_smart_matching(callback.message)
    await callback.answer()


@router.callback_query(F.data == "close_smart")
async def close_smart(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
import logging
from datetime import datetime, timezone, timedelta
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)
router = Router()


def get_analytics_keyboard():
    """Analytics klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📈 Eng ko'p qidirilgan", callback_data="analytics_top_keywords"),
                InlineKeyboardButton(text="🏢 Eng aktiv kompaniyalar", callback_data="analytics_top_companies")
            ],
            [
                InlineKeyboardButton(text="💰 Maosh statistikasi", callback_data="analytics_salary"),
                InlineKeyboardButton(text="📍 Joylar bo'yicha", callback_data="analytics_locations")
            ],
            [
                InlineKeyboardButton(text="📅 Bugungi vakansiyalar", callback_data="analytics_today"),
                InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="analytics_general")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="close_analytics")
            ]
        ]
    )


@router.message(F.text == "📊 Statistika")
async def cmd_analytics(message: Message):
    """Vakansiya statistikasi"""
    await message.answer(
        "📊 <b>Vakansiya Statistikasi</b>\n\n"
        "Bozor haqida qiziqarli ma'lumotlar:\n\n"
        "• 📈 Eng ko'p qidirilgan so'zlar\n"
        "• 🏢 Eng aktiv kompaniyalar\n"
        "• 💰 O'rtacha maoshlar\n"
        "• 📍 Eng ko'p vakansiyalar qayerda\n"
        "• 📅 Bugungi yangi vakansiyalar\n\n"
        "Tanlang:",
        reply_markup=get_analytics_keyboard(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "analytics_today")
async def analytics_today(callback: CallbackQuery):
    """Bugungi vakansiyalar"""
    try:
        async with db.pool.acquire() as conn:
            today = datetime.now(timezone.utc).date()
            
            # Bugungi vakansiyalar soni
            count = await conn.fetchval('''
                SELECT COUNT(*) FROM vacancies
                WHERE DATE(published_date) = $1
            ''', today)
            
            # Manbalar bo'yicha
            sources = await conn.fetch('''
                SELECT source, COUNT(*) as count
                FROM vacancies
                WHERE DATE(published_date) = $1
                GROUP BY source
                ORDER BY count DESC
            ''', today)
            
            text = f"📅 <b>Bugungi vakansiyalar</b>\n\n"
            text += f"📊 Jami: <b>{count}</b> ta yangi vakansiya\n\n"
            
            if sources:
                text += "📱 <b>Manbalar:</b>\n"
                for row in sources:
                    emoji = {'hh_uz': '🌐', 'telegram': '📱', 'user_post': '📢'}.get(row['source'], '🔗')
                    text += f"  {emoji} {row['source']}: {row['count']} ta\n"
            
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_analytics")]
                        ]
                    ),
                    parse_mode='HTML'
                )
            except TelegramBadRequest:
                pass
            
    except Exception as e:
        logger.error(f"Analytics today error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "analytics_top_companies")
async def analytics_companies(callback: CallbackQuery):
    """Eng aktiv kompaniyalar"""
    try:
        async with db.pool.acquire() as conn:
            # Oxirgi 30 kundagi eng aktiv kompaniyalar
            companies = await conn.fetch('''
                SELECT company, COUNT(*) as count
                FROM vacancies
                WHERE published_date > NOW() - INTERVAL '30 days'
                AND company != 'Noma''lum'
                GROUP BY company
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            text = "🏢 <b>Eng aktiv kompaniyalar</b>\n"
            text += "<i>Oxirgi 30 kun</i>\n\n"
            
            if companies:
                for i, row in enumerate(companies, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
                    text += f"{emoji} {row['company']}: <b>{row['count']}</b> ta\n"
            else:
                text += "⚠️ Ma'lumot yo'q"
            
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_analytics")]
                        ]
                    ),
                    parse_mode='HTML'
                )
            except TelegramBadRequest:
                pass
            
    except Exception as e:
        logger.error(f"Analytics companies error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "analytics_salary")
async def analytics_salary(callback: CallbackQuery):
    """Maosh statistikasi"""
    try:
        async with db.pool.acquire() as conn:
            # O'rtacha maosh
            avg_salary = await conn.fetchrow('''
                SELECT 
                    AVG(salary_min) as avg_min,
                    AVG(salary_max) as avg_max,
                    MIN(salary_min) as min_salary,
                    MAX(salary_max) as max_salary
                FROM vacancies
                WHERE salary_min IS NOT NULL
                AND published_date > NOW() - INTERVAL '30 days'
            ''')
            
            text = "💰 <b>Maosh Statistikasi</b>\n"
            text += "<i>Oxirgi 30 kun</i>\n\n"
            
            if avg_salary and avg_salary['avg_min']:
                text += f"📊 <b>O'rtacha maosh:</b>\n"
                text += f"  • Minimal: {int(avg_salary['avg_min']):,} so'm\n"
                text += f"  • Maksimal: {int(avg_salary['avg_max']):,} so'm\n\n"
                
                text += f"📈 <b>Diapazoni:</b>\n"
                text += f"  • Eng past: {int(avg_salary['min_salary']):,} so'm\n"
                text += f"  • Eng yuqori: {int(avg_salary['max_salary']):,} so'm\n"
            else:
                text += "⚠️ Maosh ma'lumoti yo'q"
            
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_analytics")]
                        ]
                    ),
                    parse_mode='HTML'
                )
            except TelegramBadRequest:
                pass
            
    except Exception as e:
        logger.error(f"Analytics salary error: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)
    
    await callback.answer()


    await callback.answer()


@router.callback_query(F.data == "analytics_top_keywords")
async def analytics_keywords(callback: CallbackQuery):
    """Eng ko'p qidirilgan so'zlar"""
    try:
        async with db.pool.acquire() as conn:
            # User filtrlaridan barcha keywordlarni yig'ish (sodda usul)
            filters = await conn.fetch("SELECT filter_data FROM users WHERE filter_data IS NOT NULL")
            
            import json
            from collections import Counter
            all_keywords = []
            for row in filters:
                try:
                    data = json.loads(row['filter_data'])
                    all_keywords.extend(data.get('keywords', []))
                except:
                    continue
            
            top_keywords = Counter(all_keywords).most_common(10)
            
            text = "📈 <b>Eng ko'p qidirilgan so'zlar</b>\n\n"
            if top_keywords:
                for i, (word, count) in enumerate(top_keywords, 1):
                    text += f"{i}. <b>{word}</b>: {count} marta\n"
            else:
                text += "⚠️ Ma'lumot yo'q"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_analytics")]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Analytics keywords error: {e}")
        await callback.answer("❌ Xatolik")
    await callback.answer()


@router.callback_query(F.data == "analytics_locations")
async def analytics_locations(callback: CallbackQuery):
    """Joylar bo'yicha statistika"""
    try:
        async with db.pool.acquire() as conn:
            locations = await conn.fetch('''
                SELECT location, COUNT(*) as count
                FROM vacancies
                WHERE location IS NOT NULL AND location != ''
                GROUP BY location
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            text = "📍 <b>Vakansiyalar joylashuvi</b>\n\n"
            if locations:
                for i, row in enumerate(locations, 1):
                    text += f"{i}. <b>{row['location']}</b>: {row['count']} ta vakansiya\n"
            else:
                text += "⚠️ Ma'lumot yo'q"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_analytics")]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Analytics locations error: {e}")
        await callback.answer("❌ Xatolik")
    await callback.answer()


@router.callback_query(F.data == "show_analytics")
@router.callback_query(F.data == "analytics_general")
async def show_analytics(callback: CallbackQuery):
    """Umumiy statistika"""
    try:
        await callback.message.edit_text(
            "📊 <b>Vakansiya Statistikasi</b>\n\n"
            "Bozor haqida qiziqarli ma'lumotlar:\n\n"
            "• 📈 Eng ko'p qidirilgan so'zlar\n"
            "• 🏢 Eng aktiv kompaniyalar\n"
            "• 💰 O'rtacha maoshlar\n"
            "• 📍 Eng ko'p vakansiyalar qayerda\n"
            "• 📅 Bugungi yangi vakansiyalar\n\n"
            "Tanlang:",
            reply_markup=get_analytics_keyboard(),
            parse_mode='HTML'
        )
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "close_analytics")
async def close_analytics(callback: CallbackQuery):
    """Yopish"""
    await callback.message.delete()
    await callback.answer()
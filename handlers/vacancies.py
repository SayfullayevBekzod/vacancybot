from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()

# Vakansiyalarni sessiyada saqlash
user_vacancies = {}

# Qidiruv jarayonidagi userlar (bir vaqtda bitta qidiruv)
searching_users = set()

# Telegram scraper instanceni import qilish
telegram_scraper_instance = None

try:
    from config import TELEGRAM_ENABLED
    if TELEGRAM_ENABLED:
        from telegram_scraper import telegram_scraper
        telegram_scraper_instance = telegram_scraper
        logger.info("✅ Telegram scraper import qilindi")
    else:
        logger.info("ℹ️ Telegram scraper o'chirilgan (config)")
except Exception as e:
    logger.warning(f"⚠️ Telegram scraper yuklanmadi: {e}")


def get_vacancy_keyboard(current_index: int, total: int, vacancy_id: str = None, is_admin: bool = False, source: str = 'hh_uz') -> InlineKeyboardMarkup:
    """Vakansiya uchun klaviatura"""
    buttons = []
    
    # Navigatsiya tugmalari
    nav_buttons = []
    
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"vac_prev_{current_index}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"📊 {current_index + 1}/{total}", callback_data="vac_count")
    )
    
    if current_index < total - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"vac_next_{current_index}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Qo'shimcha tugmalar
    action_buttons = []
    
    if vacancy_id:
        action_buttons.append(
            InlineKeyboardButton(text="💾 Saqlash", callback_data=f"vac_save_{vacancy_id}")
        )
        
        # Interview buttons
        action_buttons.append(
            InlineKeyboardButton(text="❓ Interview", callback_data=f"interview_prep_{vacancy_id}")
        )
        
        # Adminlar uchun o'chirish tugmasi (faqat user_post va telegram uchun)
        if is_admin and source != 'hh_uz':
            action_buttons.append(
                InlineKeyboardButton(text="🗑 O'chirish (Admin)", callback_data=f"delete_vacancy_{vacancy_id}")
            )
    
    action_buttons.append(
        InlineKeyboardButton(text="🔍 Yangi qidiruv", callback_data="new_search")
    )
    
    buttons.append(action_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_vacancy_to_user(message_or_callback, user_id: int, index: int):
    """Vakansiyani yuborish yoki yangilash"""
    if user_id not in user_vacancies:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("⚠️ Sessiya tugadi. Yangi qidiruv boshlang.", show_alert=True)
        return
    
    data = user_vacancies[user_id]
    vacancies = data['vacancies']
    
    if index < 0 or index >= len(vacancies):
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("⚠️ Vakansiya topilmadi", show_alert=True)
        return
    
    vacancy = vacancies[index]
    data['current_index'] = index
    
    # Vakansiyani formatlash
    from filters import vacancy_filter
    vacancy_text = vacancy_filter.format_vacancy_message(vacancy)
    
    # To'liq ma'lumot tugmasi
    url_button = InlineKeyboardButton(
        text="📄 To'liq ma'lumot",
        url=vacancy.get('url', '#')
    )
    
    # Klaviatura yaratish
    vacancy_id = vacancy.get('external_id') or vacancy.get('id')
    
    from config import ADMIN_IDS
    is_admin = user_id in ADMIN_IDS
    vacancy_source = vacancy.get('source', 'hh_uz')
    
    keyboard = get_vacancy_keyboard(index, len(vacancies), str(vacancy_id) if vacancy_id else None, is_admin, vacancy_source)
    keyboard.inline_keyboard.insert(0, [url_button])
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(
                vacancy_text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(
                vacancy_text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Vakansiya yuborishda xatolik: {e}")
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("⚠️ Xatolik yuz berdi", show_alert=True)


@router.message(F.text == "🔍 Vakansiya qidirish")
async def search_vacancies(message: Message):
    """Vakansiya qidirish - OPTIMIZED VERSION"""
    user_id = message.from_user.id
    
    # Agar user allaqachon qidirayotgan bo'lsa
    if user_id in searching_users:
        await message.answer(
            "⏳ <b>Siz allaqachon qidiruv boshlagansiz!</b>\n\n"
            "Iltimos, hozirgi qidiruv tugashini kuting.",
            parse_mode='HTML'
        )
        return
    
    from config import PREMIUM_FEATURES
    
    # Premium tekshirish
    is_premium = await db.is_premium(user_id)
    features = PREMIUM_FEATURES['premium' if is_premium else 'free']
    
    # Foydalanuvchi filtrlarini olish
    user_filter = await db.get_user_filter(user_id)
    
    if not user_filter or not user_filter.get('keywords'):
        await message.answer(
            "⚠️ <b>Avval sozlamalarni o'rnating!</b>\n\n"
            "Sizga mos vakansiyalarni topish uchun, iltimos, "
            "kalit so'zlarni va boshqa filtrlarni o'rnating.\n\n"
            "⚙️ <b>Sozlamalar</b> tugmasini bosing.",
            parse_mode='HTML'
        )
        return
    
    # Qidiruv jarayonini belgilash
    searching_users.add(user_id)
    
    # Qidiruv jarayonini boshlash
    wait_msg = await message.answer(
        "🔍 <b>Vakansiyalarni qidiryapman...</b>\n\n"
        "⏳ Bu bir necha soniya vaqt olishi mumkin.",
        parse_mode='HTML'
    )
    
    try:
        # Vakansiyalarni olish
        from scraper_api import scraper_api
        from filters import vacancy_filter
        
        keywords = user_filter.get('keywords', [])
        locations = user_filter.get('locations', ['Tashkent'])
        sources = user_filter.get('sources', ['hh_uz', 'user_post'])
        
        logger.info(f"[SEARCH] User {user_id}: keywords={keywords}, locations={locations}, sources={sources}")
        
        # Sahifalar soni
        pages = features.get('scraping_pages', 2)
        
        # Vakansiyalar ro'yxati
        vacancies = []
        sources_used = []
        
        # PARALLEL SCRAPING - hammasi bir vaqtda
        tasks = []
        
        # 1. Database'dan user-posted vakansiyalar (FAST)
        async def get_user_posted():
            try:
                logger.info("[SEARCH] Fetching user-posted vacancies...")
                async with db.pool.acquire() as conn:
                    db_vacancies = await conn.fetch('''
                        SELECT 
                            vacancy_id as external_id,
                            title,
                            company,
                            description,
                            salary_min,
                            salary_max,
                            location,
                            experience_level,
                            url,
                            source,
                            published_date
                        FROM vacancies
                        WHERE source = 'user_post'
                        AND published_date > NOW() - INTERVAL '30 days'
                        ORDER BY published_date DESC
                        LIMIT 50
                    ''')
                    
                    user_posted = [dict(row) for row in db_vacancies]
                    
                    if user_posted:
                        logger.info(f"[SEARCH] User-posted: {len(user_posted)} ta")
                        return ('Bot e\'lonlar', '📢', user_posted)
                    return None
            except Exception as e:
                logger.error(f"[SEARCH] User-posted error: {e}")
                return None
        
        tasks.append(get_user_posted())
        
        # 2. hh.uz dan scraping (PARALLEL)
        async def get_hh_uz():
            if 'hh_uz' in sources:
                try:
                    logger.info(f"[SEARCH] hh.uz scraping: pages={pages}")
                    hh_vacancies = await scraper_api.scrape_hh_uz(
                        keywords=keywords,
                        location=locations[0] if locations else 'Tashkent',
                        pages=pages
                    )
                    if hh_vacancies:
                        logger.info(f"[SEARCH] hh.uz: {len(hh_vacancies)} ta")
                        return ('hh.uz', '🌐', hh_vacancies)
                    return None
                except Exception as e:
                    logger.error(f"[SEARCH] hh.uz error: {e}")
                    return None
            return None
        
        tasks.append(get_hh_uz())
        
        # 3. Telegram kanallaridan (PARALLEL, Premium only)
        async def get_telegram():
            if 'telegram' in sources and is_premium:
                if telegram_scraper_instance and telegram_scraper_instance.is_available():
                    try:
                        logger.info("[SEARCH] Telegram scraping...")
                        
                        await telegram_scraper_instance.connect()
                        tg_vacancies = await telegram_scraper_instance.scrape_channels(limit_per_channel=30)
                        await telegram_scraper_instance.disconnect()
                        
                        if tg_vacancies:
                            # Telegram kanallarini guruhlashtirish
                            tg_channels = {}
                            for vac in tg_vacancies:
                                external_id = vac.get('external_id', '')
                                if external_id.startswith('tg_'):
                                    parts = external_id.split('_')
                                    if len(parts) >= 2:
                                        channel = parts[1]
                                        tg_channels[channel] = tg_channels.get(channel, 0) + 1
                            
                            logger.info(f"[SEARCH] Telegram: {len(tg_vacancies)} ta ({len(tg_channels)} kanal)")
                            return ('Telegram', '📱', tg_vacancies, tg_channels)
                        return None
                    except Exception as e:
                        logger.error(f"[SEARCH] Telegram error: {e}")
                        return None
            return None
        
        tasks.append(get_telegram())
        
        # PARALLEL EXECUTION - HAMMASI BIR VAQTDA!
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Natijalarni yig'ish
        for result in results:
            if result and not isinstance(result, Exception):
                if len(result) == 4:  # Telegram (with channels)
                    name, emoji, vacs, channels = result
                    vacancies.extend(vacs)
                    sources_used.append({
                        'name': name,
                        'emoji': emoji,
                        'count': len(vacs),
                        'channels': channels
                    })
                elif len(result) == 3:  # Others
                    name, emoji, vacs = result
                    vacancies.extend(vacs)
                    sources_used.append({
                        'name': name,
                        'emoji': emoji,
                        'count': len(vacs)
                    })
        
        if not vacancies:
            try:
                await wait_msg.delete()
            except:
                pass
            
            await message.answer(
                "😕 <b>Hech qanday vakansiya topilmadi</b>\n\n"
                "Iltimos:\n"
                "• Kalit so'zlarni kengaytiring\n"
                "• Boshqa shaharlarni qo'shing\n"
                "• Keyinroq qayta urinib ko'ring\n\n"
                "⚙️ Sozlamalar bo'limiga o'ting.",
                parse_mode='HTML'
            )
            return
        
        # Filtr qo'llash
        logger.info(f"[SEARCH] Filtrlash: {len(vacancies)} ta vakansiya")
        filtered_vacancies = vacancy_filter.apply_filters(vacancies, user_filter)
        logger.info(f"[SEARCH] Filtrlash natijasi: {len(filtered_vacancies)} ta")
        
        # Natijalar cheklash (free foydalanuvchilar uchun)
        max_results = features.get('max_results', 10)
        limited = False
        
        if len(filtered_vacancies) > max_results:
            filtered_vacancies = filtered_vacancies[:max_results]
            limited = True
        
        try:
            await wait_msg.delete()
        except:
            pass
        
        if not filtered_vacancies:
            await message.answer(
                "😕 <b>Filtrdan hech qanday vakansiya o'tmadi</b>\n\n"
                "Filtrlarni kengaytiring:\n"
                "• Kalit so'zlarni kamaytiring\n"
                "• Maosh talablarini pasaytiring\n"
                "• Tajriba filtrini o'zgartiring\n\n"
                "⚙️ Sozlamalar bo'limiga o'ting.",
                parse_mode='HTML'
            )
            return
        
        # Foydalanuvchi uchun vakansiyalarni saqlash
        user_vacancies[user_id] = {
            'vacancies': filtered_vacancies,
            'current_index': 0
        }
        
        # === NATIJALAR XABARI ===
        result_text = f"✅ <b>{len(filtered_vacancies)} ta vakansiya topildi!</b>\n\n"
        
        # Manbalardagi natijalar
        if sources_used:
            result_text += f"📊 <b>Manbalar:</b>\n"
            for source in sources_used:
                result_text += f"{source['emoji']} <b>{source['name']}:</b> {source['count']} ta\n"
                
                # Telegram kanallari
                if source['name'] == 'Telegram' and source.get('channels'):
                    channels_list = []
                    for channel, count in sorted(source['channels'].items(), key=lambda x: x[1], reverse=True)[:5]:
                        channels_list.append(f"  • {channel}: {count} ta")
                    if channels_list:
                        result_text += "\n".join(channels_list) + "\n"
            
            result_text += "\n"
        
        if limited:
            result_text += f"⚠️ <b>Free versiya:</b> faqat birinchi {max_results} ta natija\n"
            result_text += f"💎 <b>Premium:</b> cheksiz natijalar + Telegram kanallar\n\n"
        
        result_text += f"Vakansiyalarni birma-bir ko'ring 👇"
        
        await message.answer(result_text, parse_mode='HTML')
        
        # Birinchi vakansiyani yuborish
        await send_vacancy_to_user(message, user_id, 0)
    
    except Exception as e:
        logger.error(f"[SEARCH] Qidiruvda xatolik: {e}", exc_info=True)
        try:
            await wait_msg.delete()
        except:
            pass
        await message.answer(
            "❌ <b>Xatolik yuz berdi</b>\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring.",
            parse_mode='HTML'
        )
    
    finally:
        # Qidiruv tugadi
        searching_users.discard(user_id)


@router.callback_query(F.data.startswith("vac_next_"))
async def next_vacancy(callback: CallbackQuery):
    """Keyingi vakansiya"""
    try:
        current_index = int(callback.data.split("_")[2])
        await send_vacancy_to_user(callback, callback.from_user.id, current_index + 1)
    except Exception as e:
        logger.error(f"next_vacancy xatolik: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("vac_prev_"))
async def prev_vacancy(callback: CallbackQuery):
    """Oldingi vakansiya"""
    try:
        current_index = int(callback.data.split("_")[2])
        await send_vacancy_to_user(callback, callback.from_user.id, current_index - 1)
    except Exception as e:
        logger.error(f"prev_vacancy xatolik: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data == "vac_count")
async def show_count(callback: CallbackQuery):
    """Statistika"""
    if callback.from_user.id in user_vacancies:
        data = user_vacancies[callback.from_user.id]
        await callback.answer(
            f"📊 Vakansiya {data['current_index'] + 1} / {len(data['vacancies'])}",
            show_alert=False
        )
    else:
        await callback.answer("⚠️ Sessiya tugadi", show_alert=True)


@router.callback_query(F.data.startswith("vac_save_"))
async def save_vacancy(callback: CallbackQuery):
    """Vakansiyani saqlash"""
    try:
        vacancy_id = callback.data.split("_", 2)[2]
        await db.add_sent_vacancy(callback.from_user.id, vacancy_id, "Saqlangan")
        await callback.answer("✅ Vakansiya saqlandi!", show_alert=True)
    except Exception as e:
        logger.error(f"Vakansiya saqlashda xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "new_search")
async def new_search(callback: CallbackQuery):
    """Yangi qidiruv"""
    if callback.from_user.id in user_vacancies:
        del user_vacancies[callback.from_user.id]
    
    await callback.message.answer(
        "🔍 Yangi qidiruv uchun <b>🔍 Vakansiya qidirish</b> tugmasini bosing.",
        parse_mode='HTML'
    )
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.answer()
import asyncio
import logging
from loader import bot, dp, scheduler, logger

# Config import
from config import SCRAPING_INTERVAL
from database import db
from scraper_api import scraper_api
from filters import vacancy_filter

# Handlerlarni import qilish
from handlers import start, settings, vacancies, premium, admin

# Yangi handlerlar
try:
    from handlers import post_vacancy
    POST_VACANCY_ENABLED = True
    logger.info("✅ Post vacancy handler")
except:
    POST_VACANCY_ENABLED = False

try:
    from handlers import favorites
    FAVORITES_ENABLED = True
    logger.info("✅ Favorites handler")
except:
    FAVORITES_ENABLED = False

try:
    from handlers import notifications
    NOTIFICATIONS_ENABLED = True
    logger.info("✅ Notifications handler")
except:
    NOTIFICATIONS_ENABLED = False

try:
    from handlers import referral
    REFERRAL_ENABLED = True
    logger.info("✅ Referral handler")
except:
    REFERRAL_ENABLED = False

try:
    from handlers import analytics
    ANALYTICS_ENABLED = True
    logger.info("✅ Analytics handler")
except:
    ANALYTICS_ENABLED = False

try:
    from handlers import smart_matching
    SMART_MATCHING_ENABLED = True
    logger.info("✅ Smart matching handler")
except:
    SMART_MATCHING_ENABLED = False

try:
    from handlers import interview
    INTERVIEW_ENABLED = True
    logger.info("✅ Interview handler")
except:
    INTERVIEW_ENABLED = False

try:
    from handlers import cv_analysis
    CV_ANALYSIS_ENABLED = True
    logger.info("✅ CV Analysis handler")
except:
    CV_ANALYSIS_ENABLED = False

# Handlerlarni ro'yxatdan o'tkazish (TARTIB MUHIM!)
logger.info("Handlerlar ro'yxatga olinmoqda...")

dp.include_router(admin.router)
logger.info("  ✅ Admin handler")

if POST_VACANCY_ENABLED:
    dp.include_router(post_vacancy.router)
    logger.info("  ✅ Post vacancy handler")

if FAVORITES_ENABLED:
    dp.include_router(favorites.router)
    logger.info("  ✅ Favorites handler")

if NOTIFICATIONS_ENABLED:
    dp.include_router(notifications.router)
    logger.info("  ✅ Notifications handler")

if REFERRAL_ENABLED:
    dp.include_router(referral.router)
    logger.info("  ✅ Referral handler")

if ANALYTICS_ENABLED:
    dp.include_router(analytics.router)
    logger.info("  ✅ Analytics handler")

if SMART_MATCHING_ENABLED:
    dp.include_router(smart_matching.router)
    logger.info("  ✅ Smart matching handler")

if INTERVIEW_ENABLED:
    dp.include_router(interview.router)
    logger.info("  ✅ Interview handler")

if CV_ANALYSIS_ENABLED:
    dp.include_router(cv_analysis.router)
    logger.info("  ✅ CV Analysis handler")

dp.include_router(start.router)
logger.info("  ✅ Start handler")

dp.include_router(premium.router)
logger.info("  ✅ Premium handler")

dp.include_router(settings.router)
logger.info("  ✅ Settings handler")

dp.include_router(vacancies.router)
logger.info("  ✅ Vacancies handler")

async def auto_scrape_and_notify():
    """Avtomatik scraping va bildirishnoma - OPTIMIZED GROUPED + TELEGRAM"""
    logger.info("Avtomatik scraping boshlandi...")
    
    try:
        # 1. Telegram scraping (Global)
        telegram_vacancies = []
        try:
            from config import TELEGRAM_ENABLED
            from telegram_scraper import telegram_scraper
            
            if TELEGRAM_ENABLED and telegram_scraper and telegram_scraper.is_available():
                logger.info("📱 Telegram scraping boshlanmoqda...")
                await telegram_scraper.connect()
                telegram_vacancies = await telegram_scraper.scrape_channels(limit_per_channel=30)
                await telegram_scraper.disconnect()
                
                # Bazaga saqlash
                if telegram_vacancies:
                    tg_save_tasks = [db.add_vacancy(**v) for v in telegram_vacancies]
                    await asyncio.gather(*tg_save_tasks, return_exceptions=True)
                    logger.info(f"✅ Telegram: {len(telegram_vacancies)} ta vakansiya saqlandi")
        except Exception as e:
            logger.error(f"❌ Telegram scraping error: {e}")

        # 2. Barcha faol foydalanuvchilar va ularning filtrlarini olish
        active_users = await db.get_all_active_users()
        logger.info(f"Faol foydalanuvchilar: {len(active_users)}")
        
        if not active_users:
            return

        # 3. Qidiruvlarni guruhlash
        search_groups = {}
        batch_size = 50
        
        for i in range(0, len(active_users), batch_size):
            batch_users = active_users[i:i+batch_size]
            for user_id in batch_users:
                user_filter = await db.get_user_filter(user_id)
                if user_filter and user_filter.get('keywords'):
                    keywords = tuple(sorted(user_filter.get('keywords', [])))
                    locations = user_filter.get('locations', ['Tashkent'])
                    location = locations[0] if locations else 'Tashkent'
                    
                    group_key = (keywords, location)
                    if group_key not in search_groups:
                        search_groups[group_key] = []
                    search_groups[group_key].append(user_id)
            await asyncio.sleep(0.1)
            
        logger.info(f"Unique qidiruv guruhlari: {len(search_groups)}")
        
        # 4. Har bir guruh uchun scraping va tarqatish
        # 4. Har bir guruh uchun scraping va tarqatish (Parallel)
        semaphore = asyncio.Semaphore(5)  # Bir vaqtning o'zida 5 ta guruh
        
        async def process_group(keywords_tuple, location, user_ids):
            async with semaphore:
                try:
                    keywords = list(keywords_tuple)
                    # hh.uz scraping
                    vacancies_list = await scraper_api.scrape_hh_uz(
                        keywords=keywords, 
                        location=location,
                        pages=1
                    )
                    
                    # hh.uz vakansiyalarini saqlash
                    if vacancies_list:
                        save_tasks = [db.add_vacancy(**v) for v in vacancies_list]
                        await asyncio.gather(*save_tasks, return_exceptions=True)
                    
                    # Umumiy ro'yxat: hh.uz + Telegram
                    combined_vacancies = (vacancies_list or []) + telegram_vacancies
                    
                    if combined_vacancies:
                        await distribute_vacancies_to_group(user_ids, combined_vacancies)
                        
                except Exception as e:
                    logger.error(f"Guruh scraping xatolik ({keywords}): {e}")

        logger.info(f"Guruhlarni parallel saralash boshlandi ({len(search_groups)} guruh)...")
        tasks = [
            process_group(k, l, u) 
            for (k, l), u in search_groups.items()
        ]
        await asyncio.gather(*tasks)
                
        logger.info("Avtomatik scraping tugadi")
        
    except Exception as e:
        logger.error(f"Avtomatik scraping xatolik: {e}", exc_info=True)


async def distribute_vacancies_to_group(user_ids: list, vacancies: list):
    """Vakansiyalarni userlarga tarqatish"""
    from filters import vacancy_filter
    
    for user_id in user_ids:
        try:
            # User uchun filtrni qayta olish (yoki optimallashtirish mumkin)
            user_filter = await db.get_user_filter(user_id)
            if not user_filter:
                continue
                
            # Filtr qo'llash
            filtered_vacancies = vacancy_filter.apply_filters(vacancies, user_filter)
            
            created_count = 0
            for vacancy in filtered_vacancies[:3]:
                vacancy_id = vacancy.get('external_id') or vacancy.get('id')
                
                # Allaqachon yuborilganmi?
                is_sent = await db.is_vacancy_sent(user_id, str(vacancy_id))
                if is_sent:
                    continue
                
                # Yuborish
                try:
                    vacancy_text = vacancy_filter.format_vacancy_message(vacancy)
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🆕 <b>Yangi vakansiya!</b>\n\n{vacancy_text}",
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    if vacancy_id:
                        await db.mark_vacancy_sent(user_id, str(vacancy_id))
                    
                    created_count += 1
                    await asyncio.sleep(0.3) # User rate limit
                    
                except Exception as e:
                    logger.debug(f"Send error {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"User dist error {user_id}: {e}")


async def on_startup():
    """Bot ishga tushganda"""
    logger.info("\n" + "="*60)
    logger.info("BOT ISHGA TUSHMOQDA...")
    logger.info("="*60)
    
    # Database ga ulanish
    logger.info("1. Database'ga ulanish...")
    await db.connect()
    logger.info("   ✅ Database ulanish muvaffaqiyatli")
    
    # Scheduler ishga tushirish
    logger.info("2. Scheduler ishga tushirish...")
    scheduler.add_job(
        auto_scrape_and_notify,
        'interval',
        seconds=SCRAPING_INTERVAL,
        id='auto_scraping',
        max_instances=1,  # Faqat bitta instance
        coalesce=True,    # Bir nechta o'tkazib yuborilgan taskni birlashtirish
        misfire_grace_time=300  # 5 minut grace time
    )
    scheduler.start()
    logger.info(f"   ✅ Scheduler ishga tushdi (interval: {SCRAPING_INTERVAL}s)")
    
    # Dastlabki scrapingni darhol ishga tushirish (test uchun)
    asyncio.create_task(auto_scrape_and_notify())
    
    # Funksiyalar ro'yxati
    logger.info("\n" + "="*60)
    logger.info("FAOL FUNKSIYALAR:")
    logger.info("="*60)
    logger.info("✅ Admin panel")
    logger.info("✅ Premium boshqaruv")
    logger.info("✅ Vakansiya qidirish (hh.uz)")
    logger.info("✅ Filtrlar va sozlamalar")
    logger.info("✅ Referral sistema")
    logger.info("✅ Parallel processing (OPTIMIZED)")
    
    if POST_VACANCY_ENABLED:
        logger.info("✅ Vakansiya qo'shish (Premium)")
    
    # Telegram scraper status
    try:
        from config import TELEGRAM_ENABLED
        if TELEGRAM_ENABLED:
            logger.info("✅ Telegram scraper (Premium)")
        else:
            logger.info("⚠️  Telegram scraper (o'chirilgan)")
    except:
        logger.info("⚠️  Telegram scraper (sozlanmagan)")
    
    logger.info("="*60)
    logger.info("🚀 BOT TAYYOR! OPTIMIZED FOR SCALE")
    logger.info("="*60 + "\n")


async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("\n" + "="*60)
    logger.info("BOT TO'XTATILMOQDA...")
    logger.info("="*60)
    
    # Scheduler to'xtatish
    logger.info("1. Scheduler to'xtatish...")
    scheduler.shutdown(wait=False)
    logger.info("   ✅ Scheduler to'xtatildi")
    
    # Database dan uzilish
    logger.info("2. Database dan uzilish...")
    await db.disconnect()
    logger.info("   ✅ Database uzilish muvaffaqiyatli")
    
    # Bot session yopish
    logger.info("3. Bot session yopish...")
    await bot.session.close()
    logger.info("   ✅ Bot session yopildi")
    
    logger.info("="*60)
    logger.info("👋 BOT TO'XTATILDI")
    logger.info("="*60 + "\n")


async def main():
    """Asosiy funksiya"""
    try:
        # Startup
        await on_startup()
        
        # Botni ishga tushirish - OPTIMIZED
        await dp.start_polling(
            bot,
            polling_timeout=30,
            handle_signals=True,
            close_bot_session=False  # Session ni main() da yopamiz
        )
        
    except Exception as e:
        logger.error(f"❌ KRITIK XATOLIK: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        await on_shutdown()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Bot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"\n❌ Bot xatolik bilan to'xtadi: {e}")
        raise
"""
Telegram kanallaridan vakansiya yig'ish - TO'LIQ ISHLAYDIGAN VERSIYA

IMPORTANT: Bu modul ishlashi uchun Telethon kutubxonasi kerak:
pip install telethon
"""

import re
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Telethon import (optional)
try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
    TELETHON_AVAILABLE = True
    logger.info("✅ Telethon mavjud")
except ImportError:
    TELETHON_AVAILABLE = False
    logger.warning("⚠️ Telethon o'rnatilmagan. Telegram scraper ishlamaydi.")
    logger.warning("O'rnatish: pip install telethon")


class TelegramVacancyScraper:
    """Telegram kanallaridan vakansiya yig'ish"""
    
    def __init__(self, api_id: str = None, api_hash: str = None, phone: str = None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        
        # Vakansiya kanallari - Config dan olish
        try:
            from config import TELEGRAM_CHANNELS
            self.vacancy_channels = TELEGRAM_CHANNELS
        except ImportError:
            # Fallback agar configda bo'lmasa
            self.vacancy_channels = [
                '@vacancyuz', '@itjobsuz', '@uzdevjobs', '@tashkent_jobs',
                '@ish_uz', '@ishbozor', '@jobs_uz', '@vacancy_uz'
            ]
        
        # Vakansiya trigger so'zlari (kengroq)
        self.vacancy_triggers = [
            # O'zbekcha
            'vakansiya', 'ish', 'ishga', 'kerak', 'qidiriladi', 'talab', 'talab qilinadi',
            'xodim', 'hodim', 'ishchi', 'mutaxassis', 'bo\'sh', "bo'sh", 'o\'rni', "o'rni",
            'maosh', 'oylik', 'ish haqi', 'kompaniya', 'firma', 'tashkilot',
            
            # Inglizcha
            'vacancy', 'job', 'hiring', 'required', 'needed', 'wanted', 'position',
            'developer', 'engineer', 'designer', 'manager', 'specialist', 'assistant',
            'junior', 'middle', 'senior', 'lead', 'fullstack', 'frontend', 'backend',
            
            # Ruscha
            'вакансия', 'работа', 'требуется', 'ищем', 'нужен', 'нужна', 'сотрудник',
            'специалист', 'менеджер', 'разработчик', 'дизайнер', 'компания', 'зарплата',
            
            # Texnologiyalar
            'python', 'javascript', 'java', 'php', 'react', 'vue', 'angular',
            'django', 'flask', 'nodejs', 'laravel', 'wordpress', 'android', 'ios',
            'flutter', 'swift', 'kotlin', 'html', 'css', 'sql', 'postgresql', 'mongodb'
        ]
    
    def is_available(self) -> bool:
        """Telethon mavjudligini tekshirish"""
        available = TELETHON_AVAILABLE and self.api_id and self.api_hash
        logger.info(f"Telegram scraper available: {available}")
        return available
    
    async def connect(self):
        """Telegram ga ulanish"""
        if not self.is_available():
            raise Exception("Telethon o'rnatilmagan yoki API credentials yo'q")
        
        try:
            logger.info("Telegram ga ulanishga harakat...")
            self.client = TelegramClient('vacancy_bot_session', int(self.api_id), self.api_hash)
            await self.client.start(phone=self.phone)
            logger.info("✅ Telegram ga ulanish muvaffaqiyatli")
        except Exception as e:
            logger.error(f"❌ Telegram ulanish xatolik: {e}", exc_info=True)
            raise
    
    async def disconnect(self):
        """Uzilish"""
        if self.client:
            try:
                await self.client.disconnect()
                logger.info("Telegram disconnect")
            except Exception as e:
                logger.error(f"Disconnect xatolik: {e}")
    
    def is_vacancy_message(self, text: str) -> bool:
        """Xabar vakansiya ekanligini aniqlash"""
        if not text or len(text) < 20:
            return False
        
        text_lower = text.lower()
        
        # Exclude keywords (spam, reklama)
        exclude_keywords = [
            'купить', 'продать', 'продаю', 'куплю', 'sotish', 'sotaman',
            'reklama', 'advertisement', 'акция', 'скидка', 'chegirma'
        ]
        
        for exclude in exclude_keywords:
            if exclude in text_lower:
                return False
        
        # Trigger so'zlar bormi?
        triggers_found = 0
        for trigger in self.vacancy_triggers:
            if trigger in text_lower:
                triggers_found += 1
                if triggers_found >= 2:  # Kamida 2 ta trigger
                    return True
        
        return triggers_found >= 1  # Yoki 1 ta trigger + uzun matn
    
    def parse_vacancy_from_text(self, text: str, channel_name: str, message_id: int, date) -> Optional[Dict]:
        """Xabar matnidan vakansiyani parse qilish"""
        if not self.is_vacancy_message(text):
            return None
        
        logger.debug(f"Parsing vacancy from {channel_name}/{message_id}")
        
        # Title topish (birinchi 2 qatordan)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        title = lines[0] if lines else 'Vakansiya'
        
        # Emoji va keraksiz belgilarni tozalash
        title = re.sub(r'[#️⃣🔴🔵⚡️💼📌🔥✅❗️⭕️🟢🔴🟡⚪️💎🎯🚀📢🔔]', '', title).strip()
        
        # Title juda qisqa bo'lsa, ikkinchi qatorni ham qo'shish
        if len(title) < 15 and len(lines) > 1:
            second_line = re.sub(r'[#️⃣🔴🔵⚡️💼📌🔥✅❗️⭕️🟢🔴🟡⚪️💎🎯🚀📢🔔]', '', lines[1]).strip()
            title = f"{title} {second_line}"
        
        title = title[:150]  # Max 150 belgi
        
        if not title or len(title) < 5:
            title = 'Vakansiya'
        
        # Kompaniya topish
        company = 'Noma\'lum'
        company_patterns = [
            r'(?:компания|company|firma|kompaniya|tashkilot)[:\s]+([^\n]{3,100})',
            r'(?:в компании|at company|da)[:\s]+([^\n]{3,100})',
            r'(?:фирма|firm)[:\s]+([^\n]{3,100})'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()[:100]
                company = re.sub(r'[#️⃣🔴🔵⚡️💼📌🔥✅❗️⭕️🟢🔴🟡⚪️💎🎯🚀📢🔔]', '', company).strip()
                if company:
                    break
        
        # Maosh topish
        salary_min = None
        salary_max = None
        
        salary_patterns = [
            r'(\d+)\s*[-–—]\s*(\d+)\s*(?:млн|mln|million|миллион)?',
            r'(?:от|dan|from)\s+(\d+)',
            r'(?:до|gacha|to)\s+(\d+)',
            r'(?:зп|maosh|salary)[:\s]+(\d+)',
            r'(\d+)\s*(?:млн|mln)',
            r'(?:зарплата|oylik)[:\s]+(\d+)',
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    nums = [int(n.replace(' ', '').replace(',', '')) for n in match.groups() if n]
                    if len(nums) >= 2:
                        # Agar kichik raqamlar bo'lsa (млн format)
                        salary_min = nums[0] * 1000000 if nums[0] < 100 else nums[0]
                        salary_max = nums[1] * 1000000 if nums[1] < 100 else nums[1]
                    elif len(nums) == 1:
                        salary_min = nums[0] * 1000000 if nums[0] < 100 else nums[0]
                    break
                except:
                    pass
        
        # Joylashuv topish
        location = 'Tashkent'
        location_keywords = {
            'ташкент': 'Tashkent', 'tashkent': 'Tashkent', 'toshkent': 'Tashkent',
            'самарканд': 'Samarkand', 'samarkand': 'Samarkand', 'samarqand': 'Samarkand',
            'бухара': 'Bukhara', 'bukhara': 'Bukhara', 'buxoro': 'Bukhara',
            'андижан': 'Andijan', 'andijan': 'Andijan', 'andijon': 'Andijan',
            'фергана': 'Fergana', 'fergana': 'Fergana', "farg'ona": 'Fergana',
            'наманган': 'Namangan', 'namangan': 'Namangan',
        }
        
        text_lower = text.lower()
        for keyword, city in location_keywords.items():
            if keyword in text_lower:
                location = city
                break
        
        # Tajriba
        experience_level = 'not_specified'
        exp_keywords = {
            'no_experience': ['junior', 'джуниор', 'без опыта', 'tajribasiz', 'no experience', 'стажер', 'stajer'],
            'between_1_and_3': ['middle', 'мидл', '1-3', '2-3 года', '1-2 yil'],
            'between_3_and_6': ['3-6', '3-5 лет', '4-6 yil'],
            'more_than_6': ['senior', 'сеньор', 'lead', 'тимлид', '6+', 'более 6']
        }
        
        for level, keywords in exp_keywords.items():
            if any(kw in text_lower for kw in keywords):
                experience_level = level
                break
        
        # URL
        url = f"https://t.me/{channel_name.replace('@', '')}/{message_id}"
        
        # Date
        if isinstance(date, datetime):
            if date.tzinfo is None:
                published_date = date.replace(tzinfo=timezone.utc)
            else:
                published_date = date.astimezone(timezone.utc)
        else:
            published_date = datetime.now(timezone.utc)
        
        # Tavsif (birinchi 500 belgi, emoji tozalangan)
        description = text[:500]
        
        vacancy = {
            'external_id': f"tg_{channel_name}_{message_id}",
            'title': title,
            'company': company,
            'description': description,
            'salary_min': salary_min,
            'salary_max': salary_max,
            'location': location,
            'experience_level': experience_level,
            'url': url,
            'source': 'telegram',
            'published_date': published_date
        }
        
        logger.info(f"✅ Telegram vakansiya: {title[:50]} from {channel_name}")
        return vacancy
    
    async def scrape_channels(self, limit_per_channel: int = 30) -> List[Dict]:
        """Kanallardan vakansiyalarni yig'ish"""
        if not self.is_available():
            logger.error("Telethon mavjud emas")
            return []
        
        if not self.client:
            logger.error("Telegram client yo'q - connect() chaqiring")
            return []
        
        vacancies = []
        
        for channel in self.vacancy_channels:
            try:
                logger.info(f"📱 Kanal scraping: {channel}")
                
                # Oxirgi xabarlarni olish
                messages = []
                try:
                    async for message in self.client.iter_messages(channel, limit=limit_per_channel):
                        if message.text:
                            messages.append(message)
                except Exception as e:
                    logger.error(f"   ❌ Kanal {channel} dan xabar olishda xatolik: {e}")
                    continue
                
                logger.info(f"   {channel}: {len(messages)} ta xabar topildi")
                
                # Parse qilish
                parsed_count = 0
                for msg in messages:
                    try:
                        vacancy = self.parse_vacancy_from_text(
                            msg.text,
                            channel,
                            msg.id,
                            msg.date
                        )
                        
                        if vacancy:
                            vacancies.append(vacancy)
                            parsed_count += 1
                    except Exception as e:
                        logger.debug(f"   Parse error: {e}")
                        continue
                
                logger.info(f"   ✅ {channel}: {parsed_count} ta vakansiya parse qilindi")
                
            except Exception as e:
                logger.error(f"   ❌ Kanal {channel} scraping xatolik: {e}")
                continue
        
        logger.info(f"📱 Telegram: Jami {len(vacancies)} ta vakansiya topildi")
        return vacancies


# Global instance (agar config bor bo'lsa)
telegram_scraper = None

try:
    from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELEGRAM_ENABLED
    
    if TELEGRAM_ENABLED and TELEGRAM_API_ID and TELEGRAM_API_HASH:
        telegram_scraper = TelegramVacancyScraper(
            TELEGRAM_API_ID, 
            TELEGRAM_API_HASH, 
            TELEGRAM_PHONE
        )
        logger.info("✅ Telegram scraper yaratildi")
    else:
        logger.info("ℹ️ Telegram scraper o'chirilgan yoki credentials yo'q")
except ImportError as e:
    logger.warning(f"⚠️ Config'dan Telegram sozlamalar import qilinmadi: {e}")
except Exception as e:
    logger.error(f"❌ Telegram scraper yaratish xatolik: {e}")


# Test funksiyasi
async def test_telegram_scraper():
    """Test"""
    if not TELETHON_AVAILABLE:
        print("❌ Telethon o'rnatilmagan!")
        print("O'rnatish: pip install telethon")
        return
    
    print("\n🧪 TELEGRAM SCRAPER TEST\n")
    print("⚠️  API credentials kerak:")
    print("1. https://my.telegram.org ga kiring")
    print("2. API development tools ga o'ting")
    print("3. api_id va api_hash oling\n")
    
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    phone = input("Telefon (+998901234567): ").strip()
    
    scraper = TelegramVacancyScraper(api_id, api_hash, phone)
    
    try:
        await scraper.connect()
        vacancies = await scraper.scrape_channels(limit_per_channel=10)
        
        print(f"\n✅ {len(vacancies)} ta vakansiya topildi\n")
        
        for i, vac in enumerate(vacancies[:5], 1):
            print(f"{i}. {vac['title']}")
            print(f"   🏢 {vac['company']}")
            print(f"   📍 {vac['location']}")
            print(f"   💰 {vac.get('salary_min', 'N/A')} - {vac.get('salary_max', 'N/A')}")
            print(f"   🔗 {vac['url']}\n")
        
    finally:
        await scraper.disconnect()


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_telegram_scraper())
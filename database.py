import asyncpg
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
import asyncio

logger = logging.getLogger(__name__)


class Database:
    async def delete_vacancy(self, vacancy_id: str) -> bool:
        """Vakansiyani o'chirish"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM vacancies WHERE vacancy_id = $1",
                    vacancy_id
                )
                return "DELETE 1" in result
        except Exception as e:
            logger.error(f"Vakansiya o'chirishda xatolik: {e}")
            return False
    
    async def connect(self):
        """Ma'lumotlar bazasiga ulanish - OPTIMIZED"""
        try:
            from config import DATABASE_URL
            
            # OPTIMIZED POOL SETTINGS
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,           # Minimum 5 connection
                max_size=20,          # Maximum 20 connection (ko'p user uchun)
                max_queries=50000,    # Har bir connection uchun max queries
                max_inactive_connection_lifetime=300,  # 5 minut
                command_timeout=60,   # 60 soniya timeout
                timeout=30,           # Connection olish timeout
            )
            logger.info("✅ Database pool yaratildi (optimized: min=5, max=20)")
            await self.create_tables()
        except Exception as e:
            logger.error(f"❌ Database ulanish xatolik: {e}", exc_info=True)
            raise
    
    async def disconnect(self):
        """Ulanishni yopish"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool yopildi")
    
    async def create_tables(self):
        """Jadvallarni yaratish"""
        async with self.pool.acquire() as conn:
            # Users jadvali
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    premium_until TIMESTAMPTZ,
                    referred_by BIGINT,
                    role VARCHAR(50) DEFAULT 'seeker',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            
            # User filters jadvali
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_filters (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    keywords TEXT[],
                    locations TEXT[],
                    regions TEXT[],
                    categories TEXT[],
                    salary_min INTEGER,
                    salary_max INTEGER,
                    employment_types TEXT[],
                    experience_level VARCHAR(50),
                    sources TEXT[] DEFAULT ARRAY['hh_uz', 'user_post'],
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id)
                )
            ''')
            
            # Sent vacancies jadvali
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sent_vacancies (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    vacancy_id VARCHAR(255),
                    vacancy_title TEXT,
                    sent_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, vacancy_id)
                )
            ''')
            
            # Vacancies jadvali
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS vacancies (
                    id SERIAL PRIMARY KEY,
                    vacancy_id VARCHAR(255) UNIQUE,
                    title TEXT,
                    company VARCHAR(255),
                    location VARCHAR(255),
                    salary_min INTEGER,
                    salary_max INTEGER,
                    experience_level VARCHAR(50),
                    description TEXT,
                    url TEXT,
                    source VARCHAR(50),
                    published_date TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')

            # Resumes jadvali (Seekers)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS resumes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    full_name VARCHAR(255),
                    age INTEGER,
                    technology TEXT,
                    telegram_username VARCHAR(255),
                    phone VARCHAR(50),
                    region VARCHAR(255),
                    salary VARCHAR(255),
                    profession VARCHAR(255),
                    call_time VARCHAR(255),
                    goal TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            
            # Notification settings jadvali
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    enabled BOOLEAN DEFAULT TRUE,
                    instant_notify BOOLEAN DEFAULT TRUE,
                    daily_digest BOOLEAN DEFAULT FALSE,
                    digest_time TIME DEFAULT '20:00:00',
                    last_digest_sent TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_premium ON users(premium_until)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_sent_vacancies_user ON sent_vacancies(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_sent_vacancies_vacancy ON sent_vacancies(vacancy_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_published ON vacancies(published_date DESC)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_source ON vacancies(source)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_location ON vacancies(location)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_experience ON vacancies(experience_level)')
            
            # referred_by ustunini qo'shish (eski database uchun)
            try:
                await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT')
                logger.info("✅ referred_by ustuni qo'shildi/tekshirildi")
            except:
                pass
            
            logger.info("✅ Jadvallar va indexlar yaratildi/tekshirildi")
    
    # ========== USER MANAGEMENT - OPTIMIZED ==========
    
    async def add_resume(self, **kwargs):
        """Rezyume qo'shish"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO resumes (
                        user_id, full_name, age, technology, telegram_username, 
                        phone, region, salary, profession, call_time, goal
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''', 
                kwargs['user_id'], kwargs['full_name'], kwargs['age'], kwargs['technology'],
                kwargs['telegram_username'], kwargs['phone'], kwargs['region'], kwargs['salary'],
                kwargs['profession'], kwargs['call_time'], kwargs['goal']
                )
                return True
        except Exception as e:
            logger.error(f"❌ add_resume xatolik: {e}")
            return False

    async def get_resumes(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Rezyumelarni olish"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM resumes 
                    ORDER BY created_at DESC 
                    LIMIT $1 OFFSET $2
                ''', limit, offset)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ get_resumes xatolik: {e}")
            return []

    async def get_all_seekers_with_filters(self) -> List[Dict]:
        """Barcha ish qidiruvchilarni filtrlari bilan olish"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT u.user_id, f.keywords, f.locations, f.salary_min, f.salary_max, f.experience_level
                    FROM users u
                    JOIN user_filters f ON u.user_id = f.user_id
                    WHERE u.role = 'seeker' AND u.is_active = TRUE
                ''')
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ get_all_seekers_with_filters xatolik: {e}")
            return []

    async def add_user(self, user_id: int, username: str = None, 
                      first_name: str = None, last_name: str = None):
        """Yangi foydalanuvchi qo'shish - OPTIMIZED"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE
                    SET username = EXCLUDED.username, 
                        first_name = EXCLUDED.first_name, 
                        last_name = EXCLUDED.last_name,
                        updated_at = EXCLUDED.updated_at,
                        is_active = TRUE
                ''', user_id, username, first_name, last_name, now, now)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ add_user xatolik: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi ma'lumotlarini olish - OPTIMIZED"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT 
                        *,
                        (premium_until > $2) as is_premium_active
                    FROM users 
                    WHERE user_id = $1
                ''', user_id, now)
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"❌ get_user xatolik: {e}")
            return None
    
    async def get_all_active_users(self) -> List[int]:
        """Barcha faol foydalanuvchilar - OPTIMIZED with index"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT user_id FROM users WHERE is_active = TRUE ORDER BY user_id'
                )
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error(f"❌ get_all_active_users xatolik: {e}")
            return []
    
    # ========== PREMIUM MANAGEMENT - FIXED ==========
    
    async def set_premium(self, user_id: int, days: int) -> bool:
        """Premium berish/uzaytirish - FIXED VERSION"""
        try:
            async with self.pool.acquire() as conn:
                # 1. User tekshirish
                user_exists = await conn.fetchval(
                    'SELECT user_id FROM users WHERE user_id = $1',
                    user_id
                )
                
                if not user_exists:
                    logger.error(f"[PREMIUM] ❌ User {user_id} not found!")
                    return False
                
                # 2. Hozirgi premium status
                current_premium = await conn.fetchrow(
                    'SELECT premium_until FROM users WHERE user_id = $1',
                    user_id
                )
                
                now = datetime.now(timezone.utc)
                
                # 3. Premium muddatini hisoblash
                if current_premium and current_premium['premium_until']:
                    current_until = current_premium['premium_until']
                    
                    if current_until.tzinfo is None:
                        current_until = current_until.replace(tzinfo=timezone.utc)
                    
                    # Agar aktiv bo'lsa, uzaytirish
                    if current_until > now:
                        premium_until = current_until + timedelta(days=days)
                        logger.info(f"[PREMIUM] Extending from {current_until} by {days} days")
                    else:
                        # Tugagan, yangi boshlash
                        premium_until = now + timedelta(days=days)
                        logger.info(f"[PREMIUM] Starting new premium for {days} days")
                else:
                    # Birinchi marta
                    premium_until = now + timedelta(days=days)
                    logger.info(f"[PREMIUM] First time premium for {days} days")
                
                # 4. UPDATE
                await conn.execute('''
                    UPDATE users 
                    SET premium_until = $2, updated_at = $3
                    WHERE user_id = $1
                ''', user_id, premium_until, now)
                
                # 5. VERIFICATION
                await asyncio.sleep(0.3)
                
                verification = await conn.fetchrow('''
                    SELECT premium_until, (premium_until > $2) as is_active
                    FROM users WHERE user_id = $1
                ''', user_id, now)
                
                if verification and verification['is_active']:
                    logger.info(f"[PREMIUM] ✅ SUCCESS! User {user_id} premium ACTIVE until {verification['premium_until']}")
                    return True
                else:
                    logger.error(f"[PREMIUM] ❌ FAILED! Verification: {verification}")
                    return False
                    
        except Exception as e:
            logger.error(f"[PREMIUM] ❌ EXCEPTION: {e}", exc_info=True)
            return False
    
    async def is_premium(self, user_id: int) -> bool:
        """Premium status - CACHED with index"""
        try:
            from config import ADMIN_IDS
            if user_id in ADMIN_IDS:
                return True
                
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT (premium_until > $2) as is_active
                    FROM users 
                    WHERE user_id = $1
                ''', user_id, now)
                
                return row['is_active'] if row and row['is_active'] is not None else False
                
        except Exception as e:
            logger.error(f"❌ is_premium xatolik: {e}")
            return False
    
    # ========== FILTER MANAGEMENT - OPTIMIZED ==========
    
    async def save_user_filter(self, user_id: int, filter_data: Dict):
        """User filtrini saqlash - OPTIMIZED"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO user_filters 
                    (user_id, keywords, locations, regions, categories, salary_min, salary_max,
                     employment_types, experience_level, sources, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (user_id) DO UPDATE
                    SET keywords = EXCLUDED.keywords,
                        locations = EXCLUDED.locations,
                        regions = EXCLUDED.regions,
                        categories = EXCLUDED.categories,
                        salary_min = EXCLUDED.salary_min,
                        salary_max = EXCLUDED.salary_max,
                        employment_types = EXCLUDED.employment_types,
                        experience_level = EXCLUDED.experience_level,
                        sources = EXCLUDED.sources,
                        updated_at = EXCLUDED.updated_at
                ''', 
                user_id,
                filter_data.get('keywords', []),
                filter_data.get('locations', []),
                filter_data.get('regions', []),
                filter_data.get('categories', []),
                filter_data.get('salary_min'),
                filter_data.get('salary_max'),
                filter_data.get('employment_types', []),
                filter_data.get('experience_level'),
                filter_data.get('sources', ['hh_uz', 'user_post']),
                now, now)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ save_user_filter xatolik: {e}")
            return False
    
    async def get_user_filter(self, user_id: int) -> Dict:
        """User filtrini olish (Premium uchun Telegram-auto bilan)"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM user_filters WHERE user_id = $1',
                    user_id
                )
                
                # Default filter
                data = {
                    'keywords': [],
                    'locations': ['Tashkent'],
                    'salary_min': None,
                    'salary_max': None,
                    'experience_level': 'not_specified',
                    'sources': ['hh_uz', 'user_post']
                }
                
                if row:
                    data = dict(row)
                
                # Premium check and auto-source addition
                is_premium = await self.is_premium(user_id)
                if is_premium:
                    # sources list bo'lishini ta'minlash
                    if not data.get('sources'):
                        data['sources'] = ['hh_uz', 'user_post', 'telegram']
                    elif 'telegram' not in data['sources']:
                        # convert if it was string for some reason (asyncpg usually returns list for ARRAY)
                        data['sources'] = list(data['sources'])
                        data['sources'].append('telegram')
                else:
                    # Non-premium shouldn't have telegram
                    if data.get('sources') and 'telegram' in data['sources']:
                        data['sources'] = [s for s in data['sources'] if s != 'telegram']
                
                return data
        except Exception as e:
            logger.error(f"❌ get_user_filter xatolik: {e}")
            return {
                'keywords': [],
                'locations': ['Tashkent'],
                'salary_min': None,
                'salary_max': None,
                'experience_level': 'not_specified',
                'sources': ['hh_uz', 'user_post']
            }
    
    async def delete_user_filter(self, user_id: int):
        """User filtrini o'chirish"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('DELETE FROM user_filters WHERE user_id = $1', user_id)
                return True
        except Exception as e:
            logger.error(f"❌ delete_user_filter xatolik: {e}")
            return False
    
    # ========== VACANCY MANAGEMENT ==========
    
    async def add_vacancy(self, **kwargs):
        """Vakansiya qo'shish"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval('''
                    INSERT INTO vacancies 
                    (vacancy_id, title, company, location, salary_min, salary_max,
                     experience_level, description, url, source, published_date, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (vacancy_id) DO NOTHING
                    RETURNING id
                ''',
                kwargs.get('external_id'),
                kwargs.get('title'),
                kwargs.get('company'),
                kwargs.get('location'),
                kwargs.get('salary_min'),
                kwargs.get('salary_max'),
                kwargs.get('experience_level'),
                kwargs.get('description'),
                kwargs.get('url'),
                kwargs.get('source', 'hh_uz'),
                kwargs.get('published_date', now),
                now)
                
                return result
                
        except Exception as e:
            logger.debug(f"add_vacancy: {e}")
            return None

    async def get_vacancy(self, vacancy_id: str) -> Optional[Dict]:
        """ID bo'yicha vakansiyani olish"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM vacancies WHERE vacancy_id = $1',
                    vacancy_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ get_vacancy xatolik: {e}")
            return None
    
    # ========== SENT VACANCIES ==========
    
    async def mark_vacancy_sent(self, user_id: int, vacancy_id: str, vacancy_title: str = None):
        """Yuborilgan vakansiyani belgilash"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO sent_vacancies (user_id, vacancy_id, vacancy_title, sent_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, vacancy_id) DO NOTHING
                ''', user_id, vacancy_id, vacancy_title, now)
                
                return True
        except Exception as e:
            logger.debug(f"add_sent_vacancy: {e}")
            return False
    
    async def is_vacancy_sent(self, user_id: int, vacancy_id: str) -> bool:
        """Vakansiya yuborilganmi?"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT 1 FROM sent_vacancies WHERE user_id = $1 AND vacancy_id = $2',
                    user_id, vacancy_id
                )
                return row is not None
        except:
            return False
    
    async def remove_premium(self, user_id: int) -> bool:
        """Premium bekor qilish"""
        try:
            now = datetime.now(timezone.utc)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE users 
                    SET premium_until = NULL, updated_at = $2
                    WHERE user_id = $1
                ''', user_id, now)
                
                return True
        except Exception as e:
            logger.error(f"❌ remove_premium: {e}")
            return False

    async def get_users_for_digest(self) -> List[Dict]:
        """Xulosa yuborilishi kerak bo'lgan userlarni olish (Uzbekistan vaqti bilan)"""
        try:
            from datetime import timedelta
            now_utc = datetime.now(timezone.utc)
            # Uzbekistan vaqti (UTC+5)
            uz_now = now_utc + timedelta(hours=5)
            today = uz_now.date()
            current_time = uz_now.time()
            
            async with self.pool.acquire() as conn:
                # 1. Digest yoqilgan, bugun hali yuborilmagan va vaqti kelgan userlar
                return await conn.fetch('''
                    SELECT ns.user_id, ns.digest_time, u.premium_until
                    FROM notification_settings ns
                    JOIN users u ON ns.user_id = u.user_id
                    WHERE ns.daily_digest = TRUE 
                      AND (ns.last_digest_sent IS NULL OR ns.last_digest_sent::DATE < $1)
                      AND ns.digest_time <= $2::TIME
                ''', today, current_time)
        except Exception as e:
            logger.error(f"get_users_for_digest error: {e}")
            return []

    async def update_last_digest_sent(self, user_id: int):
        """Oxirgi xulosa vaqtini yangilash"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE notification_settings 
                    SET last_digest_sent = NOW() 
                    WHERE user_id = $1
                ''', user_id)
        except Exception as e:
            logger.error(f"update_last_digest_sent error: {e}")

    async def get_recent_vacancies_for_user(self, user_id: int, limit: int = 10) -> List[Dict]:
        """User uchun oxirgi mos vakansiyalarni olish (Digest uchun)"""
        try:
            user_filter = await self.get_user_filter(user_id)
            if not user_filter or not user_filter.get('keywords'):
                return []
            
            keywords = [f"%{k}%" for k in user_filter.get('keywords', [])]
            if not keywords: return []
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM vacancies 
                    WHERE (title ILIKE ANY($1) OR description ILIKE ANY($1))
                      AND published_date > NOW() - INTERVAL '24 hours'
                    ORDER BY published_date DESC
                    LIMIT $2
                ''', keywords, limit)
                
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_recent_vacancies_for_user error: {e}")
            return []

    async def get_referral_stats(self, user_id: int) -> Dict:
        """Referral statistikasi"""
        try:
            async with self.pool.acquire() as conn:
                # Jami referrallar soni
                total = await conn.fetchval(
                    'SELECT COUNT(*) FROM users WHERE referred_by = $1',
                    user_id
                )
                # Premium bo'lgan referrallar soni
                premium = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE referred_by = $1 AND premium_until > NOW()
                ''', user_id)
                
                return {
                    'total': total or 0,
                    'premium': premium or 0
                }
        except Exception as e:
            logger.error(f"get_referral_stats error: {e}")
            return {'total': 0, 'premium': 0}

    async def get_referral_list(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Referrallar ro'yxati"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT user_id, first_name, username, created_at,
                           (premium_until > NOW()) as is_premium
                    FROM users 
                    WHERE referred_by = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', user_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"get_referral_list error: {e}")
            return []

    async def get_top_referrers(self, limit: int = 10) -> List[Dict]:
        """Eng ko'p referral to'plaganlar"""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch('''
                    SELECT r.first_name, COUNT(u.user_id) as total
                    FROM users u
                    JOIN users r ON u.referred_by = r.user_id
                    GROUP BY r.user_id, r.first_name
                    ORDER BY total DESC
                    LIMIT $1
                ''', limit)
        except Exception as e:
            logger.error(f"get_top_referrers error: {e}")
            return []

# Global database instance
db = Database()
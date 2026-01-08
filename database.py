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
            
            # Indexlar - OPTIMIZED
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_premium ON users(premium_until)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_sent_vacancies_user ON sent_vacancies(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_sent_vacancies_vacancy ON sent_vacancies(vacancy_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_published ON vacancies(published_date DESC)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_source ON vacancies(source)')
            
            # referred_by ustunini qo'shish (eski database uchun)
            try:
                await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT')
                logger.info("✅ referred_by ustuni qo'shildi/tekshirildi")
            except:
                pass
            
            logger.info("✅ Jadvallar va indexlar yaratildi/tekshirildi")
    
    # ========== USER MANAGEMENT - OPTIMIZED ==========
    
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
    
    async def get_user_filter(self, user_id: int) -> Optional[Dict]:
        """User filtrini olish"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM user_filters WHERE user_id = $1',
                    user_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ get_user_filter xatolik: {e}")
            return None
    
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
    
    # ========== SENT VACANCIES ==========
    
    async def add_sent_vacancy(self, user_id: int, vacancy_id: str, vacancy_title: str):
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


# Global database instance
db = Database()
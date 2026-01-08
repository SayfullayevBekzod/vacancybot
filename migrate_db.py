#!/usr/bin/env python3
"""
Database Migration Script
Yangi funksiyalar uchun database'ni yangilash
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timezone

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Database connection
try:
    from config import DATABASE_URL
except ImportError:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'vacancy_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def run_migration():
    """Asosiy migration funksiyasi"""
    print("\n" + "="*70)
    print("DATABASE MIGRATION")
    print("Yangi funksiyalar uchun database yangilanmoqda...")
    print("="*70 + "\n")
    
    try:
        # 1. Database'ga ulanish
        logger.info("1️⃣ Database'ga ulanish...")
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("   ✅ Ulanish muvaffaqiyatli\n")
        
        # 2. Referral sistema
        logger.info("2️⃣ Referral sistema...")
        try:
            await conn.execute('''
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES users(user_id)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_referred_by 
                ON users(referred_by)
            ''')
            logger.info("   ✅ Referral ustun va index qo'shildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Referral migration: {e}\n")
        
        # 3. Notification settings
        logger.info("3️⃣ Notification settings jadvali...")
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                    enabled BOOLEAN DEFAULT TRUE,
                    instant_notify BOOLEAN DEFAULT TRUE,
                    daily_digest BOOLEAN DEFAULT FALSE,
                    digest_time TIME DEFAULT '18:00:00',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_notification_settings_user 
                ON notification_settings(user_id)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_notification_settings_enabled 
                ON notification_settings(enabled)
            ''')
            
            logger.info("   ✅ Notification settings yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Notification settings: {e}\n")
        
        # 4. User activity log
        logger.info("4️⃣ User activity log jadvali...")
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    activity_type VARCHAR(50),
                    vacancy_id VARCHAR(255),
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_activity_user 
                ON user_activity(user_id)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_activity_type 
                ON user_activity(activity_type)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_activity_date 
                ON user_activity(created_at)
            ''')
            
            logger.info("   ✅ User activity yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ User activity: {e}\n")
        
        # 5. Favorites extension
        logger.info("5️⃣ Favorites kengaytirish...")
        try:
            await conn.execute('''
                ALTER TABLE sent_vacancies 
                ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE
            ''')
            
            await conn.execute('''
                ALTER TABLE sent_vacancies 
                ADD COLUMN IF NOT EXISTS notes TEXT
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sent_vacancies_favorite 
                ON sent_vacancies(user_id, is_favorite)
            ''')
            
            logger.info("   ✅ Favorites ustunlari qo'shildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Favorites: {e}\n")
        
        # 6. Referral rewards
        logger.info("6️⃣ Referral rewards jadvali...")
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS referral_rewards (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    referral_count INT NOT NULL,
                    reward_days INT NOT NULL,
                    claimed_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_referral_rewards_user 
                ON referral_rewards(user_id)
            ''')
            
            logger.info("   ✅ Referral rewards yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Referral rewards: {e}\n")
        
        # 7. Vacancy analytics
        logger.info("7️⃣ Vacancy analytics jadvali...")
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS vacancy_analytics (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    source VARCHAR(50),
                    total_count INT DEFAULT 0,
                    avg_salary_min DECIMAL(12,2),
                    avg_salary_max DECIMAL(12,2),
                    top_keywords TEXT[],
                    top_companies TEXT[],
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(date, source)
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_vacancy_analytics_date 
                ON vacancy_analytics(date)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_vacancy_analytics_source 
                ON vacancy_analytics(source)
            ''')
            
            logger.info("   ✅ Vacancy analytics yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Vacancy analytics: {e}\n")
        
        # 8. Matching scores cache
        logger.info("8️⃣ Matching scores cache jadvali...")
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS matching_scores (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    vacancy_id VARCHAR(255),
                    match_score INT NOT NULL,
                    calculated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, vacancy_id)
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_matching_scores_user 
                ON matching_scores(user_id)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_matching_scores_score 
                ON matching_scores(match_score DESC)
            ''')
            
            logger.info("   ✅ Matching scores yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Matching scores: {e}\n")
        
        # 9. Triggers
        logger.info("9️⃣ Triggerlar yaratish...")
        try:
            # Update trigger function
            await conn.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            ''')
            
            # Notification settings trigger
            await conn.execute('''
                DROP TRIGGER IF EXISTS update_notification_settings_updated_at 
                ON notification_settings
            ''')
            
            await conn.execute('''
                CREATE TRIGGER update_notification_settings_updated_at
                    BEFORE UPDATE ON notification_settings
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
            ''')
            
            logger.info("   ✅ Triggerlar yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Triggers: {e}\n")
        
        # 10. Functions
        logger.info("🔟 Funksiyalar yaratish...")
        try:
            # Cleanup function
            await conn.execute('''
                CREATE OR REPLACE FUNCTION cleanup_old_data()
                RETURNS void AS $$
                BEGIN
                    DELETE FROM user_activity 
                    WHERE created_at < NOW() - INTERVAL '90 days';
                    
                    DELETE FROM matching_scores 
                    WHERE calculated_at < NOW() - INTERVAL '30 days';
                    
                    DELETE FROM vacancies 
                    WHERE published_date < NOW() - INTERVAL '180 days';
                END;
                $$ LANGUAGE plpgsql
            ''')
            
            # Stats function
            await conn.execute('''
                CREATE OR REPLACE FUNCTION get_user_stats(p_user_id BIGINT)
                RETURNS TABLE (
                    total_searches BIGINT,
                    total_saves BIGINT,
                    total_referrals BIGINT,
                    premium_until TIMESTAMPTZ
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*) FILTER (WHERE activity_type = 'search'),
                        COUNT(*) FILTER (WHERE activity_type = 'save'),
                        (SELECT COUNT(*) FROM users WHERE referred_by = p_user_id),
                        u.premium_until
                    FROM user_activity ua
                    RIGHT JOIN users u ON u.user_id = p_user_id
                    WHERE ua.user_id = p_user_id
                    GROUP BY u.premium_until;
                END;
                $$ LANGUAGE plpgsql
            ''')
            
            logger.info("   ✅ Funksiyalar yaratildi\n")
        except Exception as e:
            logger.warning(f"   ⚠️ Functions: {e}\n")
        
        # 11. Verification
        logger.info("1️⃣1️⃣ Tekshirish...")
        
        # Jadvallar soni
        tables = await conn.fetch('''
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        ''')
        
        logger.info(f"   📋 Jami jadvallar: {len(tables)}")
        for table in tables:
            logger.info(f"      • {table['tablename']}")
        
        print()
        
        # Indexlar soni
        indexes = await conn.fetch('''
            SELECT COUNT(*) as count
            FROM pg_indexes
            WHERE schemaname = 'public'
        ''')
        
        logger.info(f"   📑 Jami indexlar: {indexes[0]['count']}\n")
        
        # 12. Test data
        logger.info("1️⃣2️⃣ Test ma'lumotlar (optional)...")
        
        create_test = input("Test ma'lumotlar yaratilsinmi? (yes/no): ").strip().lower()
        
        if create_test == 'yes':
            # Test user
            test_user_id = 999999999
            
            try:
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO NOTHING
                ''', test_user_id, 'test_user', 'Test User', 
                     datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                logger.info(f"   ✅ Test user yaratildi (ID: {test_user_id})")
                
                # Test notification settings
                await conn.execute('''
                    INSERT INTO notification_settings (user_id, enabled)
                    VALUES ($1, TRUE)
                    ON CONFLICT (user_id) DO NOTHING
                ''', test_user_id)
                
                logger.info(f"   ✅ Test notification settings yaratildi\n")
                
            except Exception as e:
                logger.warning(f"   ⚠️ Test data: {e}\n")
        
        await conn.close()
        
        # Success
        print("\n" + "="*70)
        print("✅✅✅ MIGRATION MUVAFFAQIYATLI!")
        print("="*70)
        print("\n📋 Yangi jadvallar:")
        print("   • notification_settings")
        print("   • user_activity")
        print("   • referral_rewards")
        print("   • vacancy_analytics")
        print("   • matching_scores")
        print("\n📋 Yangi ustunlar:")
        print("   • users.referred_by")
        print("   • sent_vacancies.is_favorite")
        print("   • sent_vacancies.notes")
        print("\n📋 Yangi funksiyalar:")
        print("   • cleanup_old_data()")
        print("   • get_user_stats(user_id)")
        print("\n🚀 Bot tayyor ishga tushirish uchun:")
        print("   python bot.py\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ MIGRATION XATOLIK: {e}")
        logger.error("\nTekshiring:")
        logger.error("1. PostgreSQL ishlab turibdimi?")
        logger.error("2. Database credentials to'g'rimi?")
        logger.error("3. Database mavjudmi?")
        print()
        return False


async def check_database():
    """Database holatini tekshirish"""
    print("\n" + "="*70)
    print("DATABASE TEKSHIRISH")
    print("="*70 + "\n")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Jadvallar
        tables = await conn.fetch('''
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        ''')
        
        print("📋 Jadvallar:")
        for table in tables:
            print(f"   ✅ {table['tablename']}")
        
        print()
        
        # Ustunlar (users jadvali)
        columns = await conn.fetch('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        ''')
        
        print("👥 Users jadvali ustunlari:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   • {col['column_name']}: {col['data_type']} ({nullable})")
        
        print()
        
        # Yangi jadvallarni tekshirish
        new_tables = [
            'notification_settings',
            'user_activity',
            'referral_rewards',
            'vacancy_analytics',
            'matching_scores'
        ]
        
        print("🆕 Yangi jadvallar:")
        for table_name in new_tables:
            exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            ''', table_name)
            
            status = "✅ Mavjud" if exists else "❌ Yo'q"
            print(f"   {status}: {table_name}")
        
        print()
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"❌ Xatolik: {e}")


async def rollback_migration():
    """Migration'ni bekor qilish (ehtiyot uchun)"""
    print("\n" + "="*70)
    print("⚠️  MIGRATION ROLLBACK")
    print("="*70 + "\n")
    
    confirm = input("DIQQAT! Yangi jadvallar o'chiriladi. Davom etasizmi? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Bekor qilindi\n")
        return
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        logger.info("Yangi jadvallarni o'chirish...")
        
        await conn.execute('DROP TABLE IF EXISTS matching_scores CASCADE')
        logger.info("   ✅ matching_scores o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS vacancy_analytics CASCADE')
        logger.info("   ✅ vacancy_analytics o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS referral_rewards CASCADE')
        logger.info("   ✅ referral_rewards o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS user_activity CASCADE')
        logger.info("   ✅ user_activity o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS notification_settings CASCADE')
        logger.info("   ✅ notification_settings o'chirildi")
        
        logger.info("\nYangi ustunlarni o'chirish...")
        
        await conn.execute('ALTER TABLE users DROP COLUMN IF EXISTS referred_by')
        logger.info("   ✅ users.referred_by o'chirildi")
        
        await conn.execute('ALTER TABLE sent_vacancies DROP COLUMN IF EXISTS is_favorite')
        await conn.execute('ALTER TABLE sent_vacancies DROP COLUMN IF EXISTS notes')
        logger.info("   ✅ sent_vacancies ustunlari o'chirildi")
        
        await conn.close()
        
        print("\n✅ Rollback muvaffaqiyatli!")
        
    except Exception as e:
        logger.error(f"❌ Rollback xatolik: {e}")


async def main():
    """Asosiy menu"""
    print("\n🗄️  DATABASE MIGRATION TOOL\n")
    print("Tanlang:")
    print("1. Migration'ni bajarish (yangi jadvallar)")
    print("2. Database'ni tekshirish")
    print("3. Rollback (yangi jadvallarni o'chirish)")
    print("4. Chiqish")
    
    choice = input("\nTanlov (1-4): ").strip()
    
    if choice == '1':
        await run_migration()
    elif choice == '2':
        await check_database()
    elif choice == '3':
        await rollback_migration()
    else:
        print("👋 Xayr!")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  To'xtatildi")
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")
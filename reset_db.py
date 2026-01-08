import asyncio
import asyncpg
import logging
from datetime import datetime, timezone

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config'dan import
try:
    from config import DATABASE_URL
except ImportError:
    # Agar import ishlamasa, manual
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'vacancybot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def reset_database():
    """Database'ni butunlay tozalab qayta yaratish"""
    print("\n" + "="*70)
    print("🔄 DATABASE'NI QAYTA YARATISH")
    print("="*70 + "\n")
    
    try:
        # 1. Database'ga ulanish
        print("1️⃣ Database'ga ulanilmoqda...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Ulandi\n")
        
        # 2. Eski jadvallarni o'chirish
        print("2️⃣ Eski jadvallarni o'chiryapman...")
        
        await conn.execute('DROP TABLE IF EXISTS sent_vacancies CASCADE')
        print("   ✅ sent_vacancies o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS vacancies CASCADE')
        print("   ✅ vacancies o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS user_filters CASCADE')
        print("   ✅ user_filters o'chirildi")
        
        await conn.execute('DROP TABLE IF EXISTS users CASCADE')
        print("   ✅ users o'chirildi\n")
        
        # 3. Yangi jadvallarni yaratish
        print("3️⃣ Yangi jadvallarni yaratyapman...\n")
        
        # Users jadvali - TIMESTAMPTZ bilan!
        print("   📦 Users jadvali...")
        await conn.execute('''
            CREATE TABLE users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                premium_until TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        print("   ✅ Users yaratildi")
        
        # User filters jadvali
        print("   📦 User filters jadvali...")
        await conn.execute('''
            CREATE TABLE user_filters (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                keywords TEXT[],
                locations TEXT[],
                regions TEXT[],
                categories TEXT[],
                salary_min INTEGER,
                salary_max INTEGER,
                employment_types TEXT[],
                experience_level VARCHAR(50),
                sources TEXT[] DEFAULT ARRAY['hh_uz'],
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        print("   ✅ User filters yaratildi")
        
        # Vacancies jadvali
        print("   📦 Vacancies jadvali...")
        await conn.execute('''
            CREATE TABLE vacancies (
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
        print("   ✅ Vacancies yaratildi")
        
        # Sent vacancies jadvali
        print("   📦 Sent vacancies jadvali...")
        await conn.execute('''
            CREATE TABLE sent_vacancies (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                vacancy_id VARCHAR(255),
                vacancy_title TEXT,
                sent_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, vacancy_id)
            )
        ''')
        print("   ✅ Sent vacancies yaratildi\n")
        
        # 4. Indexlar yaratish
        print("4️⃣ Indexlar yaratyapman...")
        await conn.execute('CREATE INDEX idx_users_premium ON users(premium_until)')
        await conn.execute('CREATE INDEX idx_sent_vacancies_user ON sent_vacancies(user_id)')
        await conn.execute('CREATE INDEX idx_vacancies_published ON vacancies(published_date)')
        print("   ✅ Indexlar yaratildi\n")
        
        # 5. Test user qo'shish
        print("5️⃣ Test user qo'shyapman...")
        test_user_id = 123456789
        now = datetime.now(timezone.utc)
        
        await conn.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', test_user_id, 'test_user', 'Test', 'User', now, now)
        print(f"   ✅ Test user yaratildi (ID: {test_user_id})\n")
        
        # 6. Premium test
        print("6️⃣ Premium funksiyasini test qilyapman...")
        premium_until = now + timedelta(days=30)
        
        await conn.execute('''
            UPDATE users 
            SET premium_until = $2, updated_at = $3 
            WHERE user_id = $1
        ''', test_user_id, premium_until, now)
        
        # Tekshirish
        result = await conn.fetchrow('''
            SELECT 
                user_id,
                premium_until,
                (premium_until > NOW()) as is_premium
            FROM users 
            WHERE user_id = $1
        ''', test_user_id)
        
        if result and result['is_premium']:
            print(f"   ✅ Premium test muvaffaqiyatli!")
            print(f"      Premium until: {result['premium_until']}")
        else:
            print(f"   ⚠️ Premium test o'tmadi")
        
        # Test userni o'chirish
        await conn.execute('DELETE FROM users WHERE user_id = $1', test_user_id)
        print(f"   ✅ Test user o'chirildi\n")
        
        await conn.close()
        
        print("="*70)
        print("✅✅✅ DATABASE MUVAFFAQIYATLI TIKLANDI!")
        print("="*70)
        print("\n🚀 Endi botni ishga tushirishingiz mumkin:")
        print("   python main.py\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ XATOLIK: {e}")
        print("\nTekshiring:")
        print("1. PostgreSQL ishlab turibdimi?")
        print("2. .env fayli to'g'rimi?")
        print("3. Database mavjudmi? (vacancybot)")
        print("\nDatabase yaratish:")
        print("   psql -U postgres")
        print("   CREATE DATABASE vacancybot;")
        return False


async def check_database_structure():
    """Database strukturasini tekshirish"""
    print("\n" + "="*70)
    print("🔍 DATABASE STRUKTURASINI TEKSHIRISH")
    print("="*70 + "\n")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print("📋 Jadvallar:")
        for table in tables:
            print(f"   ✅ {table['table_name']}")
        print()
        
        # Users columns
        print("👥 Users jadvali ustunlari:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   • {col['column_name']}: {col['data_type']} ({nullable})")
        
        print()
        
        # Premium column check
        premium_col = await conn.fetchrow("""
            SELECT data_type 
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'premium_until'
        """)
        
        if premium_col:
            if 'timestamp' in premium_col['data_type'].lower():
                print("✅ premium_until ustuni TIMESTAMPTZ")
            else:
                print(f"⚠️ premium_until ustuni {premium_col['data_type']} (TIMESTAMPTZ bo'lishi kerak!)")
        else:
            print("❌ premium_until ustuni yo'q!")
        
        await conn.close()
        print()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}\n")


if __name__ == '__main__':
    print("\n🔧 DATABASE TIKLASH SKRIPTI\n")
    print("Tanlang:")
    print("1. Database'ni butunlay qayta yaratish (BARCHA MA'LUMOTLAR O'CHADI!)")
    print("2. Database strukturasini tekshirish")
    print("3. Chiqish")
    
    choice = input("\nTanlov (1/2/3): ").strip()
    
    if choice == '1':
        confirm = input("\n⚠️ DIQQAT! Barcha ma'lumotlar o'chadi. Davom etasizmi? (yes/no): ").strip().lower()
        if confirm == 'yes':
            asyncio.run(reset_database())
        else:
            print("❌ Bekor qilindi")
    elif choice == '2':
        asyncio.run(check_database_structure())
    else:
        print("👋 Xayr!")


# Import qo'shish
from datetime import timedelta
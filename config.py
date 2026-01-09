import os
from dotenv import load_dotenv
from datetime import timezone

# .env faylini yuklash
load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
# DB_HOST = os.getenv('DB_HOST', 'localhost')
# DB_PORT = int(os.getenv('DB_PORT', 5432))
# DB_NAME = os.getenv('DB_NAME', 'vacancy_bot')
# DB_USER = os.getenv('DB_USER', 'postgres')
# DB_PASSWORD = os.getenv('DB_PASSWORD')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi!")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL topilmadi!")
# Timezone sozlamalari
DEFAULT_TIMEZONE = timezone.utc  # UTC timezone
# Database connection string fallback
# if not DATABASE_URL:
#     DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Timezone sozlamalari
DEFAULT_TIMEZONE = timezone.utc  # UTC timezone

# Scraping sozlamalari
SCRAPING_INTERVAL = int(os.getenv('SCRAPING_INTERVAL', 600))  # 10 daqiqa

# Admin foydalanuvchilar
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]

# Telegram API (kanallardan scraping uchun)
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')
TELEGRAM_ENABLED = bool(TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_PHONE)

# Vakansiya saytlari
VACANCY_SITES = {
    'hh_uz': 'https://hh.uz/search/vacancy',
    'olx_uz': 'https://www.olx.uz/rabota/',
}


PAYMENT_INFO = {
    'card_number': '5614 6814 0308 5164',
    'card_holder': 'Sayfullayev Bekzod',
    'support_username': 'SayfullayevBekzod'
}
# Telegram kanallari (Premium foydalanuvchilar uchun)
# Telegram kanallari (Premium foydalanuvchilar uchun)
TELEGRAM_CHANNELS = [
    '@UstozShogirdSohalar',
    '@ishmi_ish',
    '@techjobs_vakansiya',
    '@vakansiyaa_ishbor',
    '@freelancer_Uzbek',
    '@freelance_uzb',
    '@Uzgrad',
    '@kasbim_uz',
    '@ish_topish',
    '@it_vacancy_uz',
    '@hr_uz',
    '@UstozShogird'
]

# Filtr sozlamalari
FILTER_KEYWORDS = [
    'python', 'django', 'flask', 'fastapi',
    'javascript', 'react', 'vue', 'nodejs',
    'developer', 'programmer', 'engineer',
    'backend', 'frontend', 'fullstack',
    'qa', 'tester', 'devops', 'designer',
    'mobile', 'android', 'ios', 'flutter'
]

# Joylashuvlar
LOCATIONS = [
    'Toshkent', 'Samarqand', 'Buxoro', 'Andijon',
    'Farg\'ona', 'Namangan', 'Nukus', 'Termiz',
    'Qarshi', 'Guliston', 'Jizzax', 'Navoiy'
]

# Premium sozlamalari
PREMIUM_FEATURES = {
    'free': {
        'max_searches_per_day': 5,
        'max_results': 10,
        'scraping_pages': 2,
        'telegram_enabled': False,
        'auto_notifications': False,
        'priority_support': False,
        'advanced_filters': False,
    },
    'premium': {
        'max_searches_per_day': 999999,  # Cheksiz
        'max_results': 999999,  # Cheksiz
        'scraping_pages': 5,
        'telegram_enabled': True,
        'auto_notifications': True,
        'priority_support': True,
        'advanced_filters': True,
    }
}

# Premium narxlari (so'm)
PREMIUM_PRICE = {
    'monthly': 25000,    # 25,000 so'm / oy
    'yearly': 250000,    # 250,000 so'm / yil (2 oy bepul)
}

# To'lov ma'lumotlari
PAYMENT_INFO = {
    'card_number': '5614 6814 0308 5164',
    'card_holder': 'Sayfullayev Bekzod',
    'support_username': 'SayfullayevBekzod'
}

# Xabar sozlamalari
MESSAGE_TEMPLATES = {
    'welcome': """
👋 Assalomu alaykum, {name}!

🤖 Men <b>Vacancy Bot</b>man. 

🎯 <b>Men nima qila olaman?</b>
• hh.uz dan vakansiyalarni avtomatik yig'aman
• Sizning talablaringizga mos vakansiyalarni filtrlayman
• Har kuni yangi vakansiyalar haqida xabar beraman

⚙️ <b>Boshlash uchun:</b>
1. "Sozlamalar" tugmasini bosing
2. O'zingizga mos filtrlarni o'rnating
3. Men sizga mos vakansiyalarni yuboraman!

Keling, boshlaymiz! 🚀
""",
    
    'premium_granted': """
🎉 <b>Tabriklaymiz!</b>

Sizga {days} kunlik Premium obuna berildi!

Endi barcha Premium imkoniyatlardan foydalanishingiz mumkin! 💎
""",
    
    'premium_expired': """
⚠️ <b>Premium obunangiz tugadi</b>

Endi siz Free versiyadan foydalanasiz.

Premium obunani yangilash uchun 💎 Premium bo'limiga o'ting.
"""
}

# Logging sozlamalari
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# API Request sozlamalari
REQUEST_TIMEOUT = 30  # soniya
MAX_RETRIES = 3
RETRY_DELAY = 5  # soniya

# Cache sozlamalari
CACHE_ENABLED = True
CACHE_TTL = 3600  # 1 soat

# Rate limiting
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_MINUTE = 60

# Scraper sozlamalari
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# Tozalash sozlamalari
CLEANUP_OLD_VACANCIES_DAYS = 30  # 30 kundan eski vakansiyalarni o'chirish
CLEANUP_INTERVAL = 86400  # 24 soat

# Debug rejimi
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Webhook sozlamalari (production uchun)
WEBHOOK_ENABLED = os.getenv('WEBHOOK_ENABLED', 'False').lower() == 'true'
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

# Server sozlamalari
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 8080))

# Backup sozlamalari
BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'False').lower() == 'true'
BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', 86400))  # 24 soat
BACKUP_PATH = os.getenv('BACKUP_PATH', './backups/')

# Monitoring
MONITORING_ENABLED = os.getenv('MONITORING_ENABLED', 'False').lower() == 'true'

# Error handling
SEND_ERROR_NOTIFICATIONS = True
ERROR_NOTIFICATION_CHAT_ID = os.getenv('ERROR_NOTIFICATION_CHAT_ID')

# Tekshirish
def validate_config():
    """Konfiguratsiya to'g'riligini tekshirish"""
    errors = []
    
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN o'rnatilmagan!")
    
    if not DB_PASSWORD:
        errors.append("❌ DB_PASSWORD o'rnatilmagan!")
    
    if not ADMIN_IDS:
        errors.append("⚠️ ADMIN_IDS o'rnatilmagan - admin funksiyalari ishlamaydi!")
    
    if errors:
        print("\n".join(errors))
        if "❌" in "\n".join(errors):
            raise ValueError("Majburiy konfiguratsiya parametrlari o'rnatilmagan!")
    
    print(f"[CONFIG] Telegram scraper: {'✅ ENABLED' if TELEGRAM_ENABLED else '❌ DISABLED'}")
    if TELEGRAM_ENABLED:
        print(f"[CONFIG] Telegram channels: {len(TELEGRAM_CHANNELS)} configured")
    else:
        print("[CONFIG] Missing: TELEGRAM_API_ID, TELEGRAM_API_HASH, or TELEGRAM_PHONE in .env")

    return True

# Konfiguratsiyani tekshirish
if __name__ == '__main__':
    try:
        validate_config()
        print("✅ Konfiguratsiya to'g'ri!")
    except Exception as e:
        print(f"❌ Konfiguratsiya xatosi: {e}")
        # config.py
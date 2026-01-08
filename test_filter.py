import asyncio
import logging
from scraper_api import scraper_api
from filters import vacancy_filter

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_filter():
    print("\n" + "="*70)
    print("🧪 FILTR TEST")
    print("="*70 + "\n")
    
    # 1. Vakansiyalarni olish
    print("1️⃣ Vakansiyalarni olyapman...\n")
    vacancies = await scraper_api.scrape_hh_uz(keywords=['python'], pages=1)
    print(f"✅ {len(vacancies)} ta vakansiya topildi\n")
    
    # 2. User filter
    user_filter = {
        'keywords': ['Python', 'Django', 'telebot'],
        'locations': ['Tashkent'],
        'min_salary': None,
        'max_salary': None,
        'experience_level': None
    }
    
    print(f"2️⃣ User filter:")
    print(f"   Keywords: {user_filter['keywords']}")
    print(f"   Locations: {user_filter['locations']}")
    print()
    
    # 3. Birinchi vakansiyani tekshirish
    if vacancies:
        vac = vacancies[0]
        print(f"3️⃣ Birinchi vakansiya:")
        print(f"   Title: {vac['title']}")
        print(f"   Company: {vac['company']}")
        print(f"   Location: {vac['location']}")
        print(f"   Description: {vac['description'][:100]}...")
        print()
        
        # Har bir filtrni alohida tekshirish
        print(f"4️⃣ Filtrlash natijalari:")
        
        keywords_ok = vacancy_filter.filter_by_keywords(vac, user_filter['keywords'])
        print(f"   Keywords filter: {keywords_ok}")
        
        location_ok = vacancy_filter.filter_by_location(vac, user_filter['locations'])
        print(f"   Location filter: {location_ok}")
        
        salary_ok = vacancy_filter.filter_by_salary(vac, user_filter.get('min_salary'), user_filter.get('max_salary'))
        print(f"   Salary filter: {salary_ok}")
        
        exp_ok = vacancy_filter.filter_by_experience(vac, user_filter.get('experience_level'))
        print(f"   Experience filter: {exp_ok}")
        print()
    
    # 5. Barcha vakansiyalarni filtrlash
    print(f"5️⃣ Barcha vakansiyalarni filtrlash...\n")
    filtered = vacancy_filter.apply_filters(vacancies, user_filter)
    
    print(f"="*70)
    print(f"✅ NATIJA: {len(vacancies)} -> {len(filtered)} ta vakansiya")
    print(f"="*70 + "\n")
    
    if filtered:
        print("Filtrlangan vakansiyalar:\n")
        for i, vac in enumerate(filtered[:5], 1):
            print(f"{i}. {vac['title']}")
            print(f"   🏢 {vac['company']}")
            print(f"   📍 {vac['location']}")
            print()
    else:
        print("⚠️  Hech qanday vakansiya filtrdan o'tmadi!\n")
        print("Muammo:")
        print("  - Kalit so'zlar vakansiya matnida yo'q")
        print("  - Joylashuv mos kelmayapti")
        print("  - Maosh yoki tajriba filtri juda qattiq\n")

if __name__ == '__main__':
    asyncio.run(test_filter())
    # test_filter.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import logging
import random

logger = logging.getLogger(__name__)
router = Router()

# Interview savollari bazasi
INTERVIEW_QUESTIONS = {
    'python': [
        "Python da list va tuple farqi nima?",
        "GIL (Global Interpreter Lock) nima va u qanday ishlaydi?",
        "Decorator nima va u qachon ishlatiladi?",
        "Generator va Iterator farqi nima?",
        "Django da MVT (Model-View-Template) arxitekturasini tushuntiring.",
        "DRF (Django Rest Framework) da Serializerlar nima uchun kerak?",
        "Asinxron dasturlash (asyncio) nima?",
        "Deep copy va Shallow copy farqi?",
        "Lambda funksiyalar nima?",
        "Python da xotira boshqaruvi (Memory Management) qanday ishlaydi?"
    ],
    'javascript': [
        "JavaScript da var, let va const farqlari?",
        "Closure nima?",
        "Event Loop qanday ishlaydi?",
        "Promise va async/await farqi?",
        "React da Virtual DOM nima?",
        "Hoisting nima?",
        "Prototype inheritance qanday ishlaydi?",
        "Callback hell nima va uni qanday oldini olish mumkin?",
        "TypeScript nima va u JavaScript dan nimasi bilan farq qiladi?",
        "Redux yoki Context API qachon ishlatiladi?"
    ],
    'java': [
        "OOP (Ob'ektga Yo'naltirilgan Dasturlash) ning 4 ta ustuni nima?",
        "Interface va Abstract class farqi?",
        "Java da Memory Management (Garbage Collection) qanday ishlaydi?",
        "JVM, JRE va JDK farqlari?",
        "Spring Boot va Spring MVC farqi?",
        "Multithreading qanday ishlaydi?",
        "HashMap va HashSet farqi?",
        "SOLID printsiplarini tushuntiring.",
        "Dependency Injection nima?",
        "Exception handling qanday ishlaydi (Checked vs Unchecked)?"
    ],
    'sql': [
        "JOIN turlari (INNER, LEFT, RIGHT, FULL) farqi nima?",
        "Index nima va u qachon ishlatiladi?",
        "ACID printsiplari nima?",
        "Normalization nima?",
        "Primary Key va Foreign Key farqi?",
        "Group By va Having farqi?",
        "Stored Procedure va Function farqi?",
        "NoSQL va SQL bazalar farqi?",
        "Transaction nima?",
        "Query optimizatsiya qanday qilinadi?"
    ],
    'hr': [
        "O'zingiz haqingizda gapirib bering.",
        "Nima uchun bizning kompaniyani tanladingiz?",
        "Kuchli va kuchsiz tomonlaringiz qanday?",
        "5 yildan keyin o'zingizni qayerda ko'rasiz?",
        "Nima uchun oldingi ish joyingizdan ketgansiz?",
        "Qiyin vaziyatlardan qanday chiqib ketasiz?",
        "Maosh bo'yicha kutilmalaringiz qanday?",
        "Jamoa bilan ishlashni yoqtirasizmi yoki yakka tartibdami?",
        "Bizga savollaringiz bormi?"
    ]
}

def get_questions_by_keyword(text: str, limit: int = 5) -> list:
    """Matn ichidan kalit so'zlarni topib, savollar qaytarish"""
    text = text.lower()
    found_questions = []
    
    # Texnik savollar
    for key, questions in INTERVIEW_QUESTIONS.items():
        if key in text:
            found_questions.extend(questions)
    
    # Agar texnik savollar topilmasa yoki kam bo'lsa, HR savollarini qo'shish
    if len(found_questions) < limit:
        found_questions.extend(INTERVIEW_QUESTIONS['hr'])
    
    # Aralashtirish va limitlash
    random.shuffle(found_questions)
    return found_questions[:limit]

@router.callback_query(F.data.startswith("interview_prep_"))
async def interview_prep(callback: CallbackQuery):
    """Interview tayyorgarlik"""
    vacancy_id = callback.data.replace("interview_prep_", "")
    
    # Vacancy ma'lumotlarini olish (Sessiyadan qidirsak tezroq bo'ladi, lekin DB ishonchli)
    vacancy = None
    
    # 1. DB dan qidirish
    try:
        # TODO: DB metodini qo'shish kerak: get_vacancy_by_id
        # Hozircha vacancy_id orqali contextdan qidiramiz
        pass 
    except:
        pass
        
    if not vacancy:
        # Fallback: Callback xabaridan 'title' ni olishga harakat qilish
        # Yoki shunchaki umumiy HR savollarini berish
        pass

    # Hozircha sodda yechim: Vacancy title/description sessiyada bo'lmasa, umumiy savollar
    # Yoki callback message textidan parse qilish
    
    text_to_analyze = callback.message.text or ""
    questions = get_questions_by_keyword(text_to_analyze)
    
    questions_text = "\n\n".join([f"❓ <b>{q}</b>" for q in questions])
    
    response = f"""
🎯 <b>Interview Savollari</b>

Ushbu vakansiya bo'yicha ehtimoliy suhbat savollari:

{questions_text}

💡 <i>Bu savollar sun'iy intellekt yordamida tanlandi.</i>
"""
    
    await callback.message.answer(response, parse_mode='HTML')
    await callback.answer()

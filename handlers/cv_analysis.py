from aiogram import Router, F
from aiogram.types import Message, ContentType
from aiogram.fsm.context import FSMContext
from database import db
from utils.cv_parser import cv_parser
from loader import bot  # Bot instance kerak faylni yuklab olish uchun
import logging
import io

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.document)
async def handle_document(message: Message):
    """Fayl qabul qilish va tahlil qilish"""
    document = message.document
    
    # Fayl turi tekshirish
    mime_type = document.mime_type
    if not mime_type or not (
        'pdf' in mime_type or 
        'word' in mime_type or 
        'octet-stream' in mime_type  # Ba'zan shunday keladi
    ):
        # Agar CV bo'lmasa, indamaymiz (boshqa maqsad uchun bo'lishi mumkin)
        return

    # Userdan tasdiq so'rash yoki caption tekshirish agar kerak bo'lsa
    # Lekin biz barcha dokumentlarni CV deb taxmin qilib ko'ramiz
    
    status_msg = await message.reply("📄 CV tahlil qilinmoqda...")
    
    try:
        # Faylni yuklab olish
        file_info = await bot.get_file(document.file_id)
        file_content = await bot.download_file(file_info.file_path)
        content_bytes = file_content.read()
        
        text = ""
        if document.file_name.lower().endswith('.pdf'):
            text = cv_parser.extract_text_from_pdf(content_bytes)
        elif document.file_name.lower().endswith('.docx'):
            text = cv_parser.extract_text_from_docx(content_bytes)
            
        logger.info(f"Extracted text length: {len(text)}")
        if not text.strip() or "ERROR" in text:
            logger.error(f"Text extraction failed. Content: '{text[:100]}...'")
            await status_msg.edit_text(
                f"⚠️ Faylni o'qib bo'lmadi.\n"
                f"Xatolik: {text}\n"
                "Iltimos, PDF yoki DOCX formatda yuboring."
            )
            return
            
        # Tahlil
        analysis = cv_parser.analyze_text(text)
        keywords = analysis.get('keywords', [])
        experience = analysis.get('experience_level')
        
        if not keywords:
            await status_msg.edit_text("🤷‍♂️ CV dan hech qanday IT ko'nikma topilmadi.")
            return
            
        # Natijani ko'rsatish va saqlash
        exp_map = {
            'no_experience': '🟢 Tajribasiz (Junior)',
            'between_1_and_3': '🟡 1-3 yil (Middle)',
            'between_3_and_6': '🟠 3-6 yil (Middle+)',
            'more_than_6': '🔴 6+ yil (Senior)',
            'not_specified': '⚪️ Aniqlanmadi'
        }
        
        # User settings update
        user_id = message.from_user.id
        user_filter = await db.get_user_filter(user_id) or {}
        
        # Eski keywordlarni saqlab qolish yoki yangilash? 
        # CV tahlili odatda "Mening profilim shu" degani, shuning uchun overwrite qilamiz
        user_filter['keywords'] = keywords
        if experience != 'not_specified':
            user_filter['experience_level'] = experience
            
        await db.save_user_filter(user_id, user_filter)
        
        await status_msg.edit_text(
            f"✅ <b>CV Tahlil qilindi va sozlamalar yangilandi!</b>\n\n"
            f"🔑 <b>Topilgan ko'nikmalar:</b>\n"
            f"{', '.join(keywords)}\n\n"
            f"👔 <b>Tajriba darajasi:</b>\n"
            f"{exp_map.get(experience)}\n\n"
            f"🔍 Endi <i>/search</i> bosib mos ishlarni qidirishingiz mumkin!",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"CV Analysis error: {e}")
        await status_msg.edit_text("❌ Xatolik yuz berdi.")

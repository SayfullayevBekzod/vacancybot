import re
import logging
import io
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CVParser:
    def __init__(self):
        # Umumiy texnologiyalar va kalit so'zlar
        self.keywords_db = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'react', 'node', 'vue', 'angular', 'typescript'],
            'java': ['java', 'spring', 'hibernate', 'jvm'],
            'c#': ['c#', '.net', 'asp.net'],
            'php': ['php', 'laravel', 'yii', 'symfony'],
            'go': ['golang', 'go lang', 'gin', 'echo'],
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'oracle', 'mongodb'],
            'devops': ['docker', 'kubernetes', 'aws', 'linux', 'ci/cd', 'git'],
            'mobile': ['flutter', 'dart', 'kotlin', 'swift', 'ios', 'android'],
            'design': ['figma', 'photoshop', 'illustrator', 'ui/ux']
        }
        
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """PDF dan matn ajratib olish"""
        text = ""
        try:
            import pypdf
            pdf_file = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except ImportError as e:
            logger.warning(f"pypdf import error: {e}")
            text = f"PDF_READ_ERROR: pypdf not installed ({e})"
        except Exception as e:
            logger.error(f"PDF o'qishda xatolik: {e}", exc_info=True)
            text = f"PDF_ERROR: {e}"
        return text

    def extract_text_from_docx(self, file_content: bytes) -> str:
        """DOCX dan matn ajratib olish"""
        text = ""
        try:
            from docx import Document
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except ImportError:
            logger.warning("python-docx kutubxonasi o'rnatilmagan")
            text = "DOCX_READ_ERROR: python-docx not installed"
        except Exception as e:
            logger.error(f"DOCX o'qishda xatolik: {e}")
        return text

    def analyze_text(self, text: str) -> Dict:
        """Matnni tahlil qilish va skillarini aniqlash"""
        text = text.lower()
        found_keywords = set()
        
        # Skillarni qidirish
        for category, keywords in self.keywords_db.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    found_keywords.add(keyword)
                    # Asosiy kategoriyani ham qo'shamiz
                    found_keywords.add(category)
        
        # Tajriba darajasini aniqlash (oddiy heuristika)
        experience = 'not_specified'
        if any(w in text for w in ['senior', 'lead', 'architect', '5+ years', '5 yil']):
            experience = 'more_than_6'
        elif any(w in text for w in ['middle', '3+ years', '3 yil', '2 yil']):
            experience = 'between_3_and_6'
        elif any(w in text for w in ['junior', 'intern', 'stajer', 'student']):
            experience = 'no_experience'
            
        return {
            'keywords': list(found_keywords),
            'experience_level': experience
        }

cv_parser = CVParser()

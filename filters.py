from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VacancyFilter:
    """Vakansiyalarni filtrlash"""
    
    @staticmethod
    def filter_by_keywords(vacancy: Dict, keywords: List[str]) -> bool:
        """Kalit so'zlar bo'yicha filtrlash"""
        if not keywords:
            return True
        
        searchable_text = (
            f"{vacancy.get('title', '')} "
            f"{vacancy.get('description', '')} "
            f"{vacancy.get('company', '')}"
        ).lower()
        
        logger.debug(f"Checking keywords {keywords} in: {searchable_text[:100]}...")
        
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                logger.debug(f"✅ Keyword '{keyword}' found!")
                return True
        
        logger.debug(f"❌ No keywords found")
        return False
    
    @staticmethod
    def filter_by_location(vacancy: Dict, locations: List[str]) -> bool:
        """Joylashuv bo'yicha filtrlash"""
        if not locations:
            return True
        
        vacancy_location = vacancy.get('location', '').lower()
        
        location_map = {
            'tashkent': ['tashkent', 'toshkent', 'ташкент', 'ташкентская область'],
            'samarkand': ['samarkand', 'samarqand', 'самарканд'],
            'bukhara': ['bukhara', 'buxoro', 'бухара'],
            'andijan': ['andijan', 'andijon', 'андижан'],
            'fergana': ['fergana', 'farg\'ona', 'фергана'],
            'namangan': ['namangan', 'наманган'],
            'nukus': ['nukus', 'нукус'],
            'termez': ['termez', 'термез'],
            'qarshi': ['qarshi', 'karshi', 'карши'],
            'gulistan': ['gulistan', 'гулистан'],
            'jizzakh': ['jizzakh', 'jizzax', 'джиззах'],
            'navoiy': ['navoiy', 'navoi', 'навои']
        }
        
        for user_location in locations:
            user_location_lower = user_location.lower()
            
            if user_location_lower in vacancy_location:
                logger.debug(f"✅ Location '{user_location}' found directly!")
                return True
            
            for key, variants in location_map.items():
                if user_location_lower in variants:
                    for variant in variants:
                        if variant in vacancy_location:
                            logger.debug(f"✅ Location '{user_location}' matched via '{variant}'!")
                            return True
        
        logger.debug(f"❌ Location not matched. Vacancy: '{vacancy_location}', User: {locations}")
        return False
    
    @staticmethod
    def filter_by_salary(vacancy: Dict, min_salary: int = None, 
                        max_salary: int = None) -> bool:
        """Maosh bo'yicha filtrlash"""
        vac_min = vacancy.get('salary_min')
        vac_max = vacancy.get('salary_max')
        
        if not vac_min and not vac_max:
            return True
        
        if min_salary:
            if vac_min and vac_min < min_salary:
                return False
            if vac_max and vac_max < min_salary:
                return False
        
        if max_salary:
            if vac_min and vac_min > max_salary:
                return False
        
        return True
    
    @staticmethod
    def filter_by_experience(vacancy: Dict, experience_level: str = None) -> bool:
        """Tajriba darajasi bo'yicha filtrlash"""
        if not experience_level:
            return True
        
        vac_experience = vacancy.get('experience_level', 'not_specified')
        
        if experience_level == vac_experience:
            return True
        
        if experience_level == 'not_specified':
            return True
        
        return False
    
    @staticmethod
    @staticmethod
    def filter_by_source(vacancy: Dict, user_sources: List[str]) -> bool:
        """Manba bo'yicha filtrlash"""
        if not user_sources:
            return True
            
        vacancy_source = vacancy.get('source', 'hh_uz')
        
        # user_post har doim ko'rinadi (agar manbalardan o'chirilmagan bo'lsa)
        if vacancy_source == 'user_post' and 'user_post' in user_sources:
            return True
            
        return vacancy_source in user_sources

    @staticmethod
    def apply_filters(vacancies: List[Dict], user_filter: Dict) -> List[Dict]:
        """Barcha filtrlarni qo'llash"""
        if not user_filter:
            return vacancies
        
        filtered = []
        user_sources = user_filter.get('sources', ['hh_uz', 'user_post'])
        
        for vacancy in vacancies:
            if not VacancyFilter.filter_by_keywords(
                vacancy, user_filter.get('keywords', [])
            ):
                continue
            
            if not VacancyFilter.filter_by_location(
                vacancy, user_filter.get('locations', [])
            ):
                continue
            
            if not VacancyFilter.filter_by_salary(
                vacancy,
                user_filter.get('min_salary'),
                user_filter.get('max_salary')
            ):
                continue
            
            if not VacancyFilter.filter_by_experience(
                vacancy, user_filter.get('experience_level')
            ):
                continue
                
            if not VacancyFilter.filter_by_source(
                vacancy, user_sources
            ):
                continue
            
            filtered.append(vacancy)
        
        logger.info(f"Filtrlash: {len(vacancies)} -> {len(filtered)}")
        return filtered
    
    @staticmethod
    def format_vacancy_message(vacancy: Dict) -> str:
        """Vakansiyani xabar formatiga o'tkazish - YAXSHILANGAN"""
        from datetime import datetime, timezone
        
        title = vacancy.get('title', 'N/A')
        company = vacancy.get('company', 'N/A')
        location = vacancy.get('location', 'N/A')
        url = vacancy.get('url', '')
        
        # Maosh
        salary_min = vacancy.get('salary_min')
        salary_max = vacancy.get('salary_max')
        
        if salary_min and salary_max:
            salary = f"{salary_min:,} - {salary_max:,} so'm"
        elif salary_min:
            salary = f"dan {salary_min:,} so'm"
        elif salary_max:
            salary = f"gacha {salary_max:,} so'm"
        else:
            salary = "Ko'rsatilmagan"
        
        # Tajriba
        exp_map = {
            'no_experience': '🟢 Tajribasiz',
            'between_1_and_3': '🟡 1-3 yil',
            'between_3_and_6': '🟠 3-6 yil',
            'more_than_6': '🔴 6+ yil',
            'not_specified': '⚪️ Ko\'rsatilmagan'
        }
        experience = exp_map.get(vacancy.get('experience_level'), '⚪️ Ko\'rsatilmagan')
        
        # E'lon qilingan vaqt
        published_date = vacancy.get('published_date')
        if published_date:
            try:
                if isinstance(published_date, datetime):
                    now = datetime.now(timezone.utc)
                    if published_date.tzinfo is None:
                        published_date = published_date.replace(tzinfo=timezone.utc)
                    
                    diff = now - published_date
                    
                    if diff.days > 0:
                        time_ago = f"{diff.days} kun oldin"
                    elif diff.seconds >= 3600:
                        hours = diff.seconds // 3600
                        time_ago = f"{hours} soat oldin"
                    elif diff.seconds >= 60:
                        minutes = diff.seconds // 60
                        time_ago = f"{minutes} daqiqa oldin"
                    else:
                        time_ago = "Hozirgina"
                else:
                    time_ago = str(published_date)[:10]
            except:
                time_ago = "Noma'lum"
        else:
            time_ago = "Noma'lum"
        
        # Tavsif
        description = vacancy.get('description', '')
        if len(description) > 300:
            description = description[:300] + '...'
        
        # ===== MANBA - YAXSHILANGAN =====
        source = vacancy.get('source', 'hh_uz')
        external_id = vacancy.get('external_id', '')
        
        # Telegram kanali nomini olish
        if source == 'telegram' and external_id.startswith('tg_'):
            try:
                # external_id formatini parse: tg_@channel_name_message_id
                parts = external_id.split('_')
                if len(parts) >= 2:
                    channel_name = parts[1]  # @channel_name
                    source_emoji = '📱'
                    source_text = f"Telegram: {channel_name}"
                else:
                    source_emoji = '📱'
                    source_text = 'TELEGRAM'
            except:
                source_emoji = '📱'
                source_text = 'TELEGRAM'
        elif source == 'hh_uz':
            source_emoji = '🌐'
            source_text = 'HH.UZ'
        elif source == 'user_post':
            source_emoji = '📢'
            source_text = 'Bot e\'loni'
        else:
            source_emoji = '🔗'
            source_text = source.upper().replace('_', ' ')
        
        # Xabar yaratish
        message = f"""
🔹 <b>{title}</b>

🏢 <b>Kompaniya:</b> {company}
💰 <b>Maosh:</b> {salary}
📍 <b>Joylashuv:</b> {location}
👔 <b>Tajriba:</b> {experience}
🕐 <b>E'lon qilingan:</b> {time_ago}
{source_emoji} <b>Manba:</b> {source_text}

📝 <b>Tavsif:</b>
{description}

🔗 <a href="{url}">Batafsil ma'lumot</a>
"""
        return message.strip()

# Global filter instance
vacancy_filter = VacancyFilter()
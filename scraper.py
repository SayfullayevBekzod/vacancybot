import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

class VacancyScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url_hh = 'https://hh.uz'
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Sahifani yuklash"""
        try:
            async with session.get(url, headers=self.headers, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Sahifa yuklashda xatolik: {url}, Status: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Sahifa yuklashda xatolik: {e}")
            return None
    
    def parse_salary(self, salary_text: str) -> tuple:
        """Maoshni parse qilish"""
        if not salary_text:
            return None, None
        
        # Raqamlarni topish
        numbers = re.findall(r'\d+\s*\d*', salary_text.replace(' ', ''))
        numbers = [int(n.replace(' ', '')) for n in numbers]
        
        if not numbers:
            return None, None
        
        if 'от' in salary_text or 'dan' in salary_text:
            return numbers[0], None
        elif 'до' in salary_text or 'gacha' in salary_text:
            return None, numbers[0]
        elif len(numbers) >= 2:
            return numbers[0], numbers[1]
        else:
            return numbers[0], numbers[0]
    
    def parse_experience(self, exp_text: str) -> str:
        """Tajriba darajasini parse qilish"""
        if not exp_text:
            return 'not_specified'
        
        exp_text = exp_text.lower()
        if 'без опыта' in exp_text or 'no experience' in exp_text:
            return 'no_experience'
        elif '1' in exp_text or 'один' in exp_text:
            return 'between_1_and_3'
        elif '3' in exp_text or 'три' in exp_text:
            return 'between_3_and_6'
        elif '6' in exp_text or 'шесть' in exp_text:
            return 'more_than_6'
        else:
            return 'not_specified'
    
    async def scrape_hh_uz(self, keywords: List[str] = None, 
                          location: str = 'Tashkent', 
                          pages: int = 5) -> List[Dict]:
        """hh.uz dan vakansiyalarni yig'ish"""
        vacancies = []
        
        async with aiohttp.ClientSession() as session:
            for page in range(pages):
                # Search URL yaratish
                search_query = ' OR '.join(keywords) if keywords else ''
                url = f"{self.base_url_hh}/search/vacancy?text={search_query}&area=2759&page={page}"
                
                logger.info(f"Scraping: {url}")
                html = await self.fetch_page(session, url)
                
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Vakansiya kartalarini topish
                vacancy_cards = soup.find_all('div', class_='vacancy-serp-item')
                
                if not vacancy_cards:
                    # Boshqa mumkin bo'lgan class nomlarini sinab ko'rish
                    vacancy_cards = soup.find_all('div', {'data-qa': 'vacancy-serp__vacancy'})
                
                logger.info(f"Topilgan vakansiyalar: {len(vacancy_cards)}")
                
                for card in vacancy_cards:
                    try:
                        vacancy = await self.parse_hh_vacancy(card, session)
                        if vacancy:
                            vacancies.append(vacancy)
                    except Exception as e:
                        logger.error(f"Vakansiyani parse qilishda xatolik: {e}")
                        continue
                
                # Har bir sahifadan keyin biroz kutish
                await asyncio.sleep(2)
        
        logger.info(f"Jami {len(vacancies)} ta vakansiya topildi")
        return vacancies
    
    async def parse_hh_vacancy(self, card, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Bitta vakansiyani parse qilish"""
        try:
            # Sarlavha va havola
            title_elem = card.find('a', {'data-qa': 'vacancy-serp__vacancy-title'})
            if not title_elem:
                title_elem = card.find('a', class_='bloko-link')
            
            if not title_elem:
                return None
            
            title = title_elem.text.strip()
            vacancy_url = title_elem['href']
            
            # External ID (URL dan olish)
            vacancy_id = vacancy_url.split('/vacancy/')[-1].split('?')[0]
            
            # Kompaniya
            company_elem = card.find('a', {'data-qa': 'vacancy-serp__vacancy-employer'})
            company = company_elem.text.strip() if company_elem else 'Noma\'lum'
            
            # Maosh
            salary_elem = card.find('span', {'data-qa': 'vacancy-serp__vacancy-compensation'})
            salary_text = salary_elem.text.strip() if salary_elem else ''
            salary_min, salary_max = self.parse_salary(salary_text)
            
            # Joylashuv
            location_elem = card.find('div', {'data-qa': 'vacancy-serp__vacancy-address'})
            location = location_elem.text.strip() if location_elem else 'Tashkent'
            
            # Qisqacha tavsif
            snippet_elem = card.find('div', {'data-qa': 'vacancy-serp__vacancy_snippet_responsibility'})
            description = snippet_elem.text.strip() if snippet_elem else ''
            
            # Tajriba
            experience_elem = card.find('div', {'data-qa': 'vacancy-serp__vacancy-work-experience'})
            experience_text = experience_elem.text.strip() if experience_elem else ''
            experience_level = self.parse_experience(experience_text)
            
            # E'lon qilingan sana
            date_elem = card.find('span', class_='vacancy-serp-item__publication-date')
            published_date = datetime.now()  # Default
            
            vacancy = {
                'external_id': f"hh_uz_{vacancy_id}",
                'title': title,
                'company': company,
                'description': description,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'location': location,
                'experience_level': experience_level,
                'url': vacancy_url if vacancy_url.startswith('http') else self.base_url_hh + vacancy_url,
                'source': 'hh_uz',
                'published_date': published_date
            }
            
            return vacancy
            
        except Exception as e:
            logger.error(f"Parse xatolik: {e}")
            return None
    
    async def scrape_vacancy_detail(self, url: str) -> Optional[str]:
        """Vakansiyaning to'liq tavsifini olish"""
        async with aiohttp.ClientSession() as session:
            html = await self.fetch_page(session, url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # To'liq tavsifni topish
            description_elem = soup.find('div', class_='vacancy-description')
            if description_elem:
                return description_elem.text.strip()
            
            return None

# Global scraper instance
scraper = VacancyScraper()


# Test funksiyasi
async def test_scraper():
    """Scraperni test qilish"""
    keywords = ['python', 'developer', 'programmer']
    vacancies = await scraper.scrape_hh_uz(keywords=keywords, pages=2)
    
    print(f"\n{'='*50}")
    print(f"Topilgan vakansiyalar: {len(vacancies)}")
    print(f"{'='*50}\n")
    
    for i, vac in enumerate(vacancies[:5], 1):
        print(f"{i}. {vac['title']}")
        print(f"   Kompaniya: {vac['company']}")
        print(f"   Maosh: {vac['salary_min']} - {vac['salary_max']}")
        print(f"   Joylashuv: {vac['location']}")
        print(f"   URL: {vac['url']}")
        print()

if __name__ == '__main__':
    asyncio.run(test_scraper())
    # scraper.py
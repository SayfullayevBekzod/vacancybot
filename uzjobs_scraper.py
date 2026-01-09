import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

class UzJobsScraper:
    """uzjobs.com saytidan vakansiyalarni yig'ish"""
    
    def __init__(self):
        self.base_url = 'https://uzjobs.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    async def scrape_uzjobs(self, keywords: List[str] = None) -> List[Dict]:
        """uzjobs.com dan vakansiyalarni yig'ish"""
        vacancies = []
        search_query = '+'.join(keywords) if keywords else ''
        
        # Qidiruv sahifasi
        url = f"{self.base_url}/ru/vacancy/search"
        params = {'q': search_query}
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"UzJobs error: {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Vakansiya bloklarini topish
                    items = soup.select('.vacancy-box') # Bu selektorni tekshirish kerak
                    if not items:
                        # Fallback selektor
                        items = soup.find_all('div', class_='vacancy-item')
                    
                    for item in items:
                        vacancy = self.parse_item(item)
                        if vacancy:
                            vacancies.append(vacancy)
                            
        except Exception as e:
            logger.error(f"UzJobs scraper error: {e}")
            
        return vacancies

    def parse_item(self, item) -> Optional[Dict]:
        """Bir dona vakansiya itemini parse qilish"""
        try:
            title_tag = item.find('a', class_='vacancy-title') or item.find('h3')
            if not title_tag: return None
            
            title = title_tag.get_text(strip=True)
            url = title_tag.get('href')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # ID extraction
            match = re.search(r'/(\d+)/?$', url)
            vacancy_id = match.group(1) if match else str(hash(url))
            
            company_tag = item.find('div', class_='company') or item.find('p', class_='employer')
            company = company_tag.get_text(strip=True) if company_tag else 'Noma\'lum'
            
            location_tag = item.find('div', class_='location') or item.find('span', class_='city')
            location = location_tag.get_text(strip=True) if location_tag else 'Tashkent'
            
            # Simple metadata
            vacancy = {
                'external_id': f"uzjobs_{vacancy_id}",
                'title': title,
                'company': company,
                'description': f"Vakansiya: {title} ({company})",
                'salary_min': None,
                'salary_max': None,
                'location': location,
                'experience_level': 'not_specified',
                'url': url,
                'source': 'uzjobs',
                'published_date': datetime.now(timezone.utc)
            }
            return vacancy
        except Exception as e:
            logger.debug(f"UzJobs item parse error: {e}")
            return None

uz_jobs_scraper = UzJobsScraper()

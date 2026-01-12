import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re

class BaseSearcher:
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

class EbaySearcher(BaseSearcher):
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        print(f"[eBay] Searching for: {query}")
        url = f"https://www.ebay.fr/sch/i.html?_nkw={query.replace(' ', '+')}&_sacat=0"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = []
            
            for item in soup.select('.s-item__wrapper')[:10]: # Limit to 10 for performance
                title_elem = item.select_one('.s-item__title')
                price_elem = item.select_one('.s-item__price')
                link_elem = item.select_one('.s-item__link')
                img_elem = item.select_one('.s-item__image-img')
                
                if title_elem and price_elem:
                    title = title_elem.text
                    price_text = price_elem.text.replace('\xa0', '').replace(' ', '')
                    price_match = re.search(r'(\d+[.,]?\d*)', price_text)
                    price = float(price_match.group(1).replace(',', '.')) if price_match else 0
                    
                    items.append({
                        'id': f"ebay_{link_elem['href'].split('/')[-1].split('?')[0]}",
                        'title': title,
                        'price': price,
                        'url': link_elem['href'],
                        'image_url': img_elem['src'] if img_elem else None,
                        'location': 'eBay',
                        'source': 'eBay',
                        'date': ''
                    })
            return items
        except Exception as e:
            print(f"[eBay Error] {e}")
            return []

class VintedSearcher(BaseSearcher):
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        print(f"[Vinted] Searching for: {query}")
        # Vinted is more complex and often requires a session cookie or a more robust scraper
        # This is a placeholder for a light version or a message
        return []

def get_multi_platform_results(query: str, platforms: Dict[str, bool], **kwargs) -> List[Dict[str, Any]]:
    all_results = []
    
    if platforms.get('ebay'):
        ebay = EbaySearcher()
        all_results.extend(ebay.search(query))
        
    if platforms.get('vinted'):
        vinted = VintedSearcher()
        all_results.extend(vinted.search(query))
        
    return all_results

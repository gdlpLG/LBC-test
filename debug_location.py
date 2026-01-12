import requests
from bs4 import BeautifulSoup
import json
import re

url = "https://www.leboncoin.fr/ad/photo_audio_video/3120142748"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for the location string in the whole text
        # Usually it's something like "Paris (75001)"
        print("--- Testing Regex Search ---")
        loc_match = re.search(r'([A-Z][a-zàâçéèêëîïôûù\s\-]+)\s?\((\d{2,5})\)', resp.text)
        if loc_match:
            print("Found regex match:", loc_match.group(0))
        
        print("--- Testing data-qa-id search ---")
        # Try finding elements with location in their class or data-qa-id
        loc_elements = soup.find_all(attrs={"data-qa-id": re.compile(r'location', re.I)})
        for el in loc_elements:
            print(f"data-qa-id={el.get('data-qa-id')}: {el.get_text().strip()}")
            
        print("--- Testing window.__REDUX_STATE__ ---")
        match = re.search(r'window\.__REDUX_STATE__\s*=\s*({.*?});', resp.text, re.DOTALL)
        if match:
            state = json.loads(match.group(1))
            ad_data = state.get('adview', {}).get('adData', {})
            print("Location from Redux:", ad_data.get('location'))
        else:
            print("Redux State not found")

        print("--- Testing LD+JSON ---")
        ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    print("LD+JSON type:", data.get('@type'))
                    if data.get('@type') == 'Product':
                        print("LD+JSON name:", data.get('name'))
                        # Check child objects for address/location
            except: pass

except Exception as e:
    print(f"Error: {e}")

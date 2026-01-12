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
        
        # Check LD+JSON
        ld_scripts = soup.find_all('script', type='application/ld+json')
        print(f"Found {len(ld_scripts)} LD+JSON scripts")
        for i, script in enumerate(ld_scripts):
            try:
                data = json.loads(script.string)
                print(f"Script {i} keys:", data.keys() if isinstance(data, dict) else "List")
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    print("Product Name:", data.get('name'))
                    print("Product Image:", data.get('image'))
                    print("Product Offers:", data.get('offers'))
            except: pass
            
        # Check all scripts for any JSON-like data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and "redux" in script.string.lower():
                print("Found redux in script")
                # Print a slice
                print(script.string[:200])
                
        # Check meta tags
        print("OG Image:", soup.find('meta', property='og:image'))
        print("OG Title:", soup.find('meta', property='og:title'))
        
        # Check for location in html
        loc_match = re.search(r'data-qa-id="adview-location-informations">(.+?)</span>', resp.text)
        if loc_match: print("Location (data-qa-id):", loc_match.group(1))
        
except Exception as e:
    print(f"Error: {e}")

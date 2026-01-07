from model import Search
from lbc import Client, Sort
from .id import ID
from .logger import logger

import time
import threading
import random
from typing import List, Union

class Searcher:
    def __init__(self, searches: Union[List[Search], Search], request_verify: bool = True):
        self._searches: List[Search] = searches if isinstance(searches, list) else [searches]
        self._request_verify = request_verify
        self._id = ID()
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]

    def _search(self, search: Search) -> None:
        client = Client(proxy=search.proxy, request_verify=self._request_verify)
        while True:
            before = time.time()
            try:
                response = client.search(**search.parameters._kwargs, sort=Sort.NEWEST)
                logger.debug(f"Successfully found {response.total} ad{'s' if response.total > 1 else ''}.")
                ads = [ad for ad in response.ads if self._id.add(ad.id)]
                if len(ads):
                    logger.info(f"Successfully found {len(ads)} new ad{'s' if len(ads) > 1 else ''}!")
                for ad in ads:
                    search.handler(ad, search.name)
            except:
                logger.exception(f"An error occured.")
            
            # Randomized human-like delay (base delay + random offset)
            actual_delay = search.delay + random.randint(-60, 180) 
            wait_time = max(30, actual_delay - (time.time() - before))
            time.sleep(wait_time)

    def start(self) -> bool:
        # Load from DB if no searches provided
        if not self._searches:
            import database
            from lbc import City
            from config import handle
            from model import Search, Parameters
            
            db_searches = database.get_active_searches()
            for s in db_searches:
                try:
                    loc = None
                    if s['lat'] and s['lng']:
                        loc = [City(lat=s['lat'], lng=s['lng'], radius=s['radius']*1000, city=s['city'])]
                    elif s['city']:
                        # Fallback simple if no coordinates (less precise)
                        loc = [City(lat=0, lng=0, city=s['city'])] # This might not work well without coordinates
                    
                    params = Parameters(text=s['query_text'], locations=loc, price=(s['price_min'], s['price_max']))
                    self._searches.append(Search(name=s['name'], parameters=params, handler=handle, delay=random.randint(900, 1500)))
                except Exception as e:
                    logger.warning(f"Could not load search '{s['name']}' from DB: {e}")

        if not len(self._searches):
            logger.warning("No search rules found in DB or config.")
            return False

        for search in self._searches:
            threading.Thread(target=self._search, args=(search,), name=search.name, daemon=True).start()
            logger.info(f"Started watch: {search.name}")
            time.sleep(5) 
        return True

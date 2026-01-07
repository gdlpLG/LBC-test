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
            time.sleep(search.delay - (time.time() - before) if search.delay - (time.time() - before) > 0 else 0)

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
```
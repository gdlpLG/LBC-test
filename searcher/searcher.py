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
            import json
            for s in db_searches:
                try:
                    locations = []
                    # 1. Load multiple locations if present
                    if s.get('locations'):
                        try:
                            stored_locs = json.loads(s['locations'])
                            for loc_data in stored_locs:
                                l_type = loc_data.get('type')
                                l_val = loc_data.get('value')
                                if l_type == 'city':
                                    # We might need to re-resolve coords if they aren't in the JSON
                                    # but usually they are (lat/lng/radius). Let's check.
                                    # If not, we'll use a fallback or skip.
                                    if 'lat' in loc_data and 'lng' in loc_data:
                                        locations.append(City(
                                            lat=loc_data['lat'], 
                                            lng=loc_data['lng'], 
                                            radius=int(loc_data.get('radius', 10))*1000,
                                            city=l_val
                                        ))
                                elif l_type == 'department':
                                    from lbc import Department
                                    try: locations.append(getattr(Department, l_val))
                                    except: pass
                                elif l_type == 'region':
                                    from lbc import Region
                                    try: locations.append(getattr(Region, l_val))
                                    except: pass
                        except Exception as e:
                            logger.error(f"Error parsing locations for {s['name']}: {e}")

                    # 2. Fallback to main search location if list is empty
                    if not locations and s['lat'] and s['lng']:
                        locations.append(City(lat=s['lat'], lng=s['lng'], radius=s['radius']*1000, city=s['city']))

                    # 3. Handle multiple keywords (separated by comma or stored as is)
                    # We'll support both single string and comma-separated for OR search behavior
                    queries = [q.strip() for q in s['query_text'].split(',')] if ',' in s['query_text'] else [s['query_text']]
                    
                    for q in queries:
                        if not q: continue
                        params = Parameters(
                            text=q, 
                            locations=locations if locations else None, 
                            price=(s['price_min'], s['price_max'])
                        )
                        # Create a Search object for each keyword to run them in parallel/sequence
                        # We append the keyword to the name to distinguish them in logs
                        search_name = f"{s['name']} ({q})" if len(queries) > 1 else s['name']
                        self._searches.append(Search(
                            name=search_name, 
                            parameters=params, 
                            handler=handle, 
                            delay=random.randint(900, 1500)
                        ))
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

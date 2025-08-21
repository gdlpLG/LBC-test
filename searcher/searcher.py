from models import Search
from lbc import Client, Sort
from .id import ID
from .logger import logger

import time
import threading
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
        if not len(self._searches):
            logger.warning("No search rules have been set. Please create search rules in config.py (see example in README.md).")
            return False

        for search in self._searches:
            threading.Thread(target=self._search, args=(search,), name=search.name).start()
            time.sleep(5) # Add latency between each thread to prevent spam
        return True
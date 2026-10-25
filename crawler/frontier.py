import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty
import time
from collections import defaultdict
from urllib.parse import urlparse
from utils import get_logger, get_urlhash, normalize
from scraper import is_valid, database

def domain_of(url):
    return ".".join(urlparse(url).hostname.split(".")[-3:])

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.lock = RLock() #creates a lock so only one worker at a time
        self.active_workers = 0 #tracks how many workers are processing pages currently
        self.to_be_downloaded = defaultdict(list)
        self.next_ok = defaultdict(float)
        
        if not os.path.exists(self.config.save_file) and not restart:
            # Save file does not exist, but request to load save.
            self.logger.info(
                f"Did not find save file {self.config.save_file}, "
                f"starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            # Save file does exists, but request to start from seed.
            self.logger.info(
                f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)
        # Load existing save file, or create one if it does not exist.
        self.save = shelve.open(self.config.save_file)

        summary_path = os.path.splitext(self.config.save_file)[0]+"_summary.json"
        if not restart and not os.path.exists(summary_path):
            if any(handled for _, handled in self.save.values()):
                raise FileNotFoundError("Missing the crawl summary file: "+summary_path)
        # not self.safe chks if we have nothing saved
        database.load(summary_path, restart=not self.save or restart)
        if restart:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.save)
        tbd_count = 0
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded[domain_of(url)].append(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")

 # Prevent multiple workers from accessing the URL list simultaneously
    def get_tbd_url(self):
        with self.lock:
            now = time.monotonic()
            for domain, urls in self.to_be_downloaded.items():
                if urls and self.next_ok[domain] <= now:
                    self.next_ok[domain] = now + 0.5
                    self.active_workers += 1
                    return urls.pop()
            return None

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)
        
        with self.lock:
            if urlhash not in self.save:
                self.save[urlhash] = (url, False)
                self.to_be_downloaded[domain_of(url)].append(url)
        
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)

        with self.lock:
            if urlhash not in self.save:
                self.logger.error(
                    f"Completed url {url}, but have not seen it before."
                )
            else:
                self.save[urlhash] = (url, True)
                self.save.sync()

            self.active_workers -= 1
            
    # Check whether all URLs have been processed
    def is_finished(self):
        with self.lock:
            return (
                not any(self.to_be_downloaded.values())
                and self.active_workers == 0
            )

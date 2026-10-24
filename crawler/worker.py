from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time


class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                # Stops when no URLs  waiting and no active workers
                if self.frontier.is_finished():
                    self.logger.info("All URLs have been processed. Stopping worker.")
                    break

                # delay since  workers may still discover more URLs
                time.sleep(0.1)
                continue


            #resp = download(tbd_url, self.config, self.logger)
            #self.logger.info(
            #    f"Downloaded {tbd_url}, status <{resp.status}>, "
            #    f"using cache {self.config.cache_server}.")
            #scraped_urls = scraper.scraper(tbd_url, resp)
            #for scraped_url in scraped_urls:
            #    self.frontier.add_url(scraped_url)
            #self.frontier.mark_url_complete(tbd_url)

            try:
                resp = download(tbd_url, self.config, self.logger)

                self.logger.info(
                    f"Downloaded {tbd_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}."
                )

                scraped_urls = scraper.scraper(tbd_url, resp)

                for scraped_url in scraped_urls:
                    self.frontier.add_url(scraped_url)

            except Exception:
                # Logs error without crashing worker
                self.logger.exception(f"Error processing {tbd_url}")

            finally:
                # release worker's active slot
                self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)

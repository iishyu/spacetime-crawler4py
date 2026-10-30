import tokenizer
import re
from urllib.parse import urlparse, urljoin, urldefrag, urlsplit, quote
import threading
from bs4 import BeautifulSoup

from utils.Database import Database

database = Database()
database_lock = threading.Lock()
MAX_BYTES_THRESHOLD = 5 * 1024**2
TRAP = re.compile(
    # calendars, iCal exports, /YYYY/MM/ archives, date params, Apache sort links
    r"(calendar|[?&]ical=|/\d{4}/\d{2}/|[?&](date|month|year)="
    r"|[?&;]C=[NMSD]|[?&;]O=[AD]"
    r"|[?&](do|rev|idx|share|replytocom|version|format|action|tab_files)="
    # grape.ics.uci.edu: timeline/changeset/log views, all refused (403)
    r"|grape\.ics\.uci\.edu/(.*/)?(timeline|changeset|log|browser|report|query|attachment)(/|\?|$)"
    # flamingo source/release trees: folder listings of code
    r"|flamingo\.ics\.uci\.edu/(releases|toolkit/src)"
    r")", re.I)

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


# used for handling non-ascii urls, and converting them into ascii-form while preserving
# important parts of url (like : // ?)
def to_ascii_url(url):
    url = url.strip()

    if url.isascii():
        return url

    # builds url while omitting things that are important to url (safe like :// ? etc)
    return quote(url, safe=":/?#[]@!$&'()*+,;=%~") # double chk if this is exhaustive of every url pattern


def extract_words(soup):
    for tag in soup(["script", "style", "noscript"]): tag.decompose()
    text = soup.get_text(" ", strip=True)
    return tokenizer.tokenize_text(text)

def normalize_url(url):
    # Splits the url into parts
    p = urlparse(url)

    # Makes host lowercase
    netloc = p.netloc.lower()
    
    # Removes default ports 
    if netloc.endswith(":80") or netloc.endswith(":443"):
        netloc = netloc.rsplit(":", 1)[0]
    
    # Removes trailing slashes
    path = p.path.rstrip("/") or "/"

    # Rebuilds url with the cleaned parts
    return p._replace(scheme=p.scheme.lower(), netloc=netloc, path=path).geturl()

# Extracts hyperlinks from a webpage, converting them into absolute URLs,
# while also removing URL fragments and duplicates, returning the cleaned links
def extract_next_links(url, resp):
    # List to hold URLS
    links = []

    # Checks whether webpage loaded - 200 = webpage loaded successfully 
    if resp.status != 200 or resp.raw_response is None:
        return links

    # Checks if page is HTML
    content_type = resp.raw_response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type:
        return links

    # Gets the HTML content from the webpage
    content = resp.raw_response.content

    # Skip the empty pages
    if not content or (len(content) > MAX_BYTES_THRESHOLD):
        return links

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")

    # Use final URL
    base_url = resp.raw_response.url or resp.url or url
    page_url = normalize_url(urldefrag(base_url)[0])

    if not is_valid(page_url):
        return links

    with database_lock:
        # If unique, add to database
        if not database.checked(page_url):
            words = extract_words(soup)
            freqs = tokenizer.computeWordFrequencies(words)
            fingerprint = database.generate_fingerprint(freqs)

            # Skip near duplicates
            if database.is_similar(fingerprint):
                database.add(page_url, {})
            else:
                database.add(page_url, freqs)

                # save every 50 pages
                if database.get_unique_page_count() % 50 == 0:
                    database.save()

    # Find all hyperlinks
    # searches HTML for <a> tags that have href attribute
    for tag in soup.find_all("a", href=True):

        # extracts url from htmlhyperlink
        href = tag["href"]

        # Try-except so that invalid urls dont crash crawler (it just keeps going)
        try:
            # Absolute URL convert
            absolute_url = urljoin(base_url, href)

            # Removes the fragments
            clean_url, fragment = urldefrag(absolute_url)
            clean_url = normalize_url(clean_url)
        except ValueError:
            # consider logging this later to understand if there's bug
            continue

        # converts url to ascii form, maintaining expected url structure (non-ascii will cause errors)
        links.append(to_ascii_url(clean_url))

    return list(set(links))

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        urls = { "ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu" }
        if parsed.scheme not in {"http", "https"}:
            return False

        hostname = parsed.hostname
        if hostname is None:
            return False

        valid_address = False
        for domain in urls:
            if hostname == domain or hostname.endswith("."+domain):
                valid_address = True
                break
        if not valid_address:
            return False

        if len(url) > 250:
            return False

        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) > 10:
            return False

        if any(segments.count(s) > 2 for s in segments):
            return False

        if TRAP.search(url):
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", url)
        raise
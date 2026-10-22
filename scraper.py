import re
from urllib.parse import urlparse, urljoin, urldefrag, urlsplit, quote
from bs4 import BeautifulSoup

MAX_BYTES_THRESHOLD = 50 * 1024**2

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
    return quote(url, safe=':/?=%~&#@') # double chk if this is exhaustive of every url pattern

# Extracts hyperlinks from a webpage, converting them into absolute URLs,
# while also removing URL fragments and duplicates, returning the cleaned links
def extract_next_links(url, resp):
    # List to hold URLS
    links = []

    # Checks whether webpage loaded - 200 = webpage loaded successfully 
    if resp.status != 200 or resp.raw_response is None:
        return links

    # Gets the HTML content from the webpage
    content = resp.raw_response.content

    # Skip the empty pages
    if not content or (len(content) > MAX_BYTES_THRESHOLD):
        return links

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")

    # Use final URL
    base_url = resp.url or url

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
        if parsed.scheme not in set(["http", "https"]):
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
        print ("TypeError for ", parsed)
        raise

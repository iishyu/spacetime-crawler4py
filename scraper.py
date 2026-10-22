import tokenize
import re
from urllib.parse import urlparse

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    links = []

    # Check if the webpage loaded
    if resp.status != 200 or resp.raw_response is None:
        return links

    # Get HTML content
    content = resp.raw_response.content

    # Skip empty pages
    if not content:
        return links

    # Parse HTML
    soup = BeautifulSoup(content, "html.parser")

    # Use final URL
    base_url = resp.url or url

    # Find all hyperlinks
    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        # Convert to absolute URL
        absolute_url = urljoin(base_url, href)

        # Remove fragments
        clean_url, fragment = urldefrag(absolute_url)

        links.append(clean_url)

    return list(set(links))

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        urls = { "ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu" }
        if parsed.scheme not in set(["http", "https"]):
            return False
        if parsed.netloc not in urls:
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
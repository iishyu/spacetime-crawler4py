import tokenizer
import hashlib
from collections import Counter
import os,json
from urllib.parse import urldefrag,urlparse

RAW_STOP_WORDS = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any',
        'are', "aren't", 'as', 'at',
        'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
        "can't", 'cannot', 'could',
        "couldn't", 'did', "didn't", 'do', 'does', "doesn't", 'doing', "don't", 'down',
        'during', 'each', 'few', 'for',
        'from', 'further', 'had', "hadn't", 'has', "hasn't", 'have', "haven't", 'having', 'he',
        "he'd", "he'll", "he's",
        'her', 'here', "here's", 'hers', 'herself', 'him', 'himself', 'his', 'how', "how's",
        'i', "i'd", "i'll", "i'm",
        "i've", 'if', 'in', 'into', 'is', "isn't", 'it', "it's", 'its', 'itself', "let's", 'me',
        'more', 'most', "mustn't",
        'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
        'ought', 'our', 'ours',
        'ourselves', 'out', 'over', 'own', 'same', "shan't", 'she', "she'd", "she'll", "she's",
        'should', "shouldn't",
        'so', 'some', 'such', 'than', 'that', "that's", 'the', 'their', 'theirs', 'them',
        'themselves', 'then', 'there',
        "there's", 'these', 'they', "they'd", "they'll", "they're", "they've", 'this', 'those',
        'through', 'to', 'too',
        'under', 'until', 'up', 'very', 'was', "wasn't", 'we', "we'd", "we'll", "we're",
        "we've", 'were', "weren't",
        'what', "what's", 'when', "when's", 'where', "where's", 'which', 'while', 'who',
        "who's", 'whom', 'why', "why's",
        'with', "won't", 'would', "wouldn't", 'you', "you'd", "you'll", "you're", "you've",
        'your', 'yours', 'yourself',
        'yourselves'
    }

STOP_WORDS = {tok for w in RAW_STOP_WORDS for tok in tokenizer.tokenize_text(w)}

#Filters out stop words, letter, and numeric tokens
def is_meaningful_word(word):
    if word in STOP_WORDS:
        return False

    if len(word) < 2:
        return False

    if not any(c.isalpha() for c in word):
        return False

    return True

def is_word(word):
    return len(word) >= 2 and any(c.isalpha() for c in word)

class Database:
    def __init__(self):
        self.db = {}
        self.words = Counter()
        self.fingerprints = set()
        self.save_path = None

    def get_unique_page_count(self):
            return len(self.db)
    
    def get_longest_page(self):
        if not self.db:
            return None, 0

        url = None
        biggest_word_count = -1
        for pg, freqs in self.db.items():
            word_count = sum(freq for word,freq in freqs.items() if is_word(word))
            if word_count>biggest_word_count:
                biggest_word_count=word_count
                url = pg
        return url,sum(self.db[url].values())


    def load(self, path, restart=False):
        self.save_path = path
        if restart:
            self.save()
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                pages = json.load(f)
        except FileNotFoundError:
            self.save()
            return

        for url, freqs in pages.items():
            self.add(url, freqs)



    def save(self):
        if self.save_path is None:
            raise RuntimeError("save() was called before load(), please call load() first (self.save_path isnt set)")

        #  ensurse that we cleanly write the file (may be issue in json dump or smth), last thing we want is our data getting wiped because of some json error.  
        path_temp = self.save_path+".temp"
        with open(path_temp, "w", encoding="utf-8") as f:
            json.dump(self.db, f)
        os.replace(path_temp, self.save_path)

    def get_summary(self):
        url, count = self.get_longest_page()
        subdoms = self.get_subdomains()
        return { "unique_pages": self.get_unique_page_count(),
            "longest_page": {"url": url, "word_count": count},
            "most_common_words": self.get_50_most_common(),
            "ics_subdomain_count": len(subdoms),
            "ics_subdomains": subdoms,
        }
    

    def add(self, url, url_dict):
        url, _ = urldefrag(url)
        if self.checked(url):
            return

        self.db[url] = url_dict

        for word, freq in url_dict.items():
            if word not in STOP_WORDS:
                self.words[word] += freq

        if url_dict:
            self.fingerprints.add(self.generate_fingerprint(url_dict))

    def get_50_most_common(self):
        filtered_words = [
            (word, count)
            for word, count in self.words.items()
            if is_meaningful_word(word)
        ]

        filtered_words.sort(key=lambda item: (-item[1], item[0]))

        return filtered_words[:50]

    def get_subdomains(self):
        subdomains = {}
        for url in self.db:
            clean_url, _ = urldefrag(url)
            hostname = urlparse(clean_url).hostname
            if hostname is None or not (
                hostname == "ics.uci.edu"
                or hostname.endswith(".ics.uci.edu")
            ):
                continue
            if hostname not in subdomains:
                subdomains[hostname] = set()
            subdomains[hostname].add(clean_url)

        res = []
        for hostname in sorted(subdomains):
            count = len(subdomains[hostname])
            res.append((f"http://{hostname}", count))
        return res

    def checked(self, url):
        url, _ = urldefrag(url)
        return url in self.db

    def generate_fingerprint(self, freqs):
        vec = [0] * 64

        for word, freq in freqs.items():
            if word in STOP_WORDS:
                continue

            digest = hashlib.md5(word.encode("utf-8")).digest()
            h = int.from_bytes(digest[:8], "big")

            for i in range(64):
                bit = (h >> i) & 1
                if bit == 1:
                    vec[i] += freq
                else:
                    vec[i] -= freq

        fingerprint = 0

        for i in range(len(vec)):
            if vec[i] > 0:
                fingerprint |= 1 << i

        return fingerprint

    def is_similar(self, fingerprint, threshold=3):
        for seen in self.fingerprints:
            diff = bin(seen ^ fingerprint).count("1")
            if diff <= threshold: return True

        return False
import tokenizer
import hashlib
import heapq
from collections import Counter
from urllib.parse import urldefrag,urlparse

STOP_WORDS = {
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

class Database:
    def __init__(self):
        self.db = {}
        self.words = Counter()
        self.fingerprints = set()

    def add(self, url, url_dict):
        self.db[url] = url_dict

        for word, freq in url_dict:
            if word not in STOP_WORDS:
                self.words[word] += freq

        self.fingerprints.add(self.generate_fingerprint(url))

    def get_50_most_common(self):
        most_common = self.words.most_common(50)

        return [word for word, freq in most_common]

    def get_subdomains(self):
        subdomains = {}
        for url in self.db:
            clean_url, _ = urldefrag(url)
            hostname = urlparse(clean_url).hostname
            if not hostname.endswith(".ics.uci.edu"):
                continue
            if hostname not in subdomains:
                subdomains[hostname] = set()
            subdomains[hostname].add(clean_url)

        res = []
        for hostname in sorted(subdomains):
            count = len(subdomains[hostname])
            res.append((hostname, count))
        return res

    def checked(self, url):
        return url in self.db

    def generate_fingerprint(self, url):
        vec = [0] * 64

        for word, freq in self.db[url].items():
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
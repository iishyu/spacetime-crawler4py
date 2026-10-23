import sys

# Reads the file line by line and builds tokens one character at a time.
# Any ASCII letter or digit gets lowercased and added to the current token,
# and anything else (spaces, punctuation, non-English characters) ends it.
#
# Runtime: O(n), linear in the number of characters n in the file. Each
# character is looked at exactly once, and the checks and append are constant
# time. Joining a token costs its length, and all the token lengths together
# add up to at most n, so that's still linear overall.
# Memory: O(n), since every token in the file ends up in the returned list.
def tokenize(file_path):
    res = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            current = []
            for ch in line:
                if ch.isalnum() and ch.isascii():
                    current.append(ch.lower())
                elif current:
                    res.append("".join(current))
                    current = []
            if current:
                res.append("".join(current))
        
    return res

def tokenize_text(text):
    words = []
    cur = []
    for char in text:
        if char.isalnum() and char.isascii():
            cur.append(char.lower())
        elif cur:
            words.append("".join(cur))
            cur = []
    if cur:
        words.append("".join(cur))
    return words

# Counts how many times each token appears using a dictionary that maps
# token -> count. get(token, 0) returns 0 the first time we see a token.
#
# Runtime: O(t), linear in the number of tokens t. Each dictionary lookup and
# update is O(1) on average since dicts are hash tables.
# Memory: O(u), where u is the number of unique tokens.
def computeWordFrequencies(tokens):
    freq = {}
    
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1

    return freq

# Sorts the (token, count) pairs and prints them. The sort key is (-count,
# token): negating the count puts the highest frequencies first, and when two
# counts tie, the token itself breaks the tie alphabetically.
#
# Runtime: O(u log u) for sorting the u unique tokens, plus O(u) to print them,
# so the sort dominates. This is the most expensive step in Part A, but some
# sorting is unavoidable since the output has to be ordered.
def printFrequencies(freq):
    res = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
    for token, count in res:
        print(token, count)


# Tokenizes both files with PartA.tokenize and turns each token list into a
# set. A set only keeps one copy of each token, so a word that appears 50 times
# in a file still only counts once. The & operator then keeps just the tokens
# that are in both sets, and the size of that is the answer.
#
# Runtime: O(n + m), linear in the total number of characters across both
# files (n and m). Tokenizing each file is linear, building each set is O(t)
# on average for t tokens, and the intersection is O(min of the two set
# sizes) on average, since Python checks each token of the smaller set against
# the larger one.
# Memory: tokenize builds the full token list for a file before it becomes a
# set, so peak memory grows with the size of the larger file, not just the
# number of unique words. 
def find_intersection(first_path, second_path):
    first = set(tokenize(first_path))
    second = set(tokenize(second_path))

    return len(first & second)
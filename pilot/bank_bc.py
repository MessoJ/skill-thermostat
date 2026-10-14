"""Pools B (mid-study) and C (final) items: six matched pairs b07..b12 / c07..c12 with identical d."""

ITEMS = [
    # ---------------------------------------------------------------- pool B
    dict(
        id="b07", pool="B", d=-0.8, title="Count negatives",
        prompt="Return how many numbers in the list are strictly less than zero (zero itself does not count). An empty list gives 0.",
        sig="count_negatives(nums)",
        ref="""def count_negatives(nums):
    total = 0
    for n in nums:
        if n < 0:
            total += 1
    return total
""",
        cases=[
            ([4, -2, 7, -9, 0],),
            ([1, 2, 3],),
            ([],),
            ([-5],),
            ([0, 0],),
            ([-1, -1, -1, 2],),
            ([-3, -2, -1],),
            ([10, -10, 10, -10, 10, -10],),
        ],
    ),
    dict(
        id="b08", pool="B", d=-0.4, title="Name initials",
        prompt="Return the first letter of each space-separated word in the string, uppercased and joined together. Words are separated by single spaces, and an empty string gives ''.",
        sig="initials(name)",
        ref="""def initials(name):
    out = ""
    for word in name.split(" "):
        if word:
            out += word[0].upper()
    return out
""",
        cases=[
            ("ada lovelace",),
            ("grace brewster hopper",),
            ("",),
            ("x",),
            ("ADA LOVELACE",),
            ("jean-luc picard",),
            ("Alan Mathison Turing",),
            ("mary ann evans",),
        ],
    ),
    dict(
        id="b09", pool="B", d=0.0, title="Top scorer",
        prompt="scores maps player names to integer scores. Return the name with the highest score; if several share it, return the alphabetically first of them (plain string comparison). Return None for an empty dict.",
        sig="top_scorer(scores)",
        ref="""def top_scorer(scores):
    if not scores:
        return None
    best = max(scores.values())
    return min(name for name, s in scores.items() if s == best)
""",
        cases=[
            ({"ann": 90, "bob": 72, "cy": 85},),
            ({"zed": 3, "amy": 8},),
            ({},),
            ({"solo": -5},),
            ({"bo": 10, "al": 10, "cy": 10},),
            ({"a": -3, "b": -1},),
            ({"mia": 7, "leo": 9, "ned": 9, "ivy": 2},),
            ({"p": 0, "q": 0},),
        ],
    ),
    dict(
        id="b10", pool="B", d=0.4, title="Order words",
        prompt="Return a new list of the words sorted by length from longest to shortest; words of equal length are ordered alphabetically (a to z). Duplicates are kept.",
        sig="order_words(words)",
        ref="""def order_words(words):
    return sorted(words, key=lambda w: (-len(w), w))
""",
        cases=[
            (["pear", "fig", "apple", "kiwi"],),
            (["bb", "a", "cc"],),
            ([],),
            (["x"],),
            (["to", "to", "a"],),
            (["dog", "cat", "ant"],),
            (["abc", "ab", "abcd", "a"],),
            (["plum", "fig", "date", "lime", "pear", "kiwi"],),
        ],
    ),
    dict(
        id="b11", pool="B", d=0.8, title="Expand ranges",
        prompt="spec is comma-separated items, each either a whole number like '5' or an inclusive range like '2-4'. Return the list of all numbers in the order written, with ranges expanded; the empty string gives []. Numbers are non-negative and there are no spaces.",
        sig="expand_ranges(spec)",
        ref="""def expand_ranges(spec):
    out = []
    if spec == "":
        return out
    for item in spec.split(","):
        if "-" in item:
            lo, hi = item.split("-")
            for n in range(int(lo), int(hi) + 1):
                out.append(n)
        else:
            out.append(int(item))
    return out
""",
        cases=[
            ("1-3,5",),
            ("4,2",),
            ("",),
            ("4-4",),
            ("0-2",),
            ("10-12,3",),
            ("5-7,1-2",),
            ("8,8-9",),
        ],
    ),
    dict(
        id="b12", pool="B", d=1.2, title="Longest distinct stretch",
        prompt="Return the length of the longest contiguous stretch of the string in which no character appears twice (case-sensitive). An empty string gives 0.",
        sig="longest_distinct_stretch(s)",
        ref="""def longest_distinct_stretch(s):
    best = 0
    start = 0
    last = {}
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best
""",
        cases=[
            ("abcabcbb",),
            ("bbbb",),
            ("pwwkew",),
            ("",),
            ("a",),
            ("abba",),
            ("dvdf",),
            ("abcdef",),
            ("tmmzuxt",),
        ],
    ),
    # ---------------------------------------------------------------- pool C
    dict(
        id="c07", pool="C", d=-0.8, title="Odd-length words",
        prompt="Return how many strings in the list have an odd number of characters (the empty string has 0 characters, which is even). An empty list gives 0.",
        sig="count_odd_lengths(words)",
        ref="""def count_odd_lengths(words):
    total = 0
    for w in words:
        if len(w) % 2 == 1:
            total += 1
    return total
""",
        cases=[
            (["cat", "horse", "at", "a"],),
            (["to", "be"],),
            ([],),
            (["a"],),
            (["", ""],),
            (["a", "a", "a", "aa"],),
            (["a", "bbb", "ccccc"],),
            (["ab", "abc", "ab", "abc", "ab", "abc"],),
        ],
    ),
    dict(
        id="c08", pool="C", d=-0.4, title="Final letters",
        prompt="Return the last letter of each space-separated word in the string, lowercased and joined together. Words are separated by single spaces, and an empty string gives ''.",
        sig="final_letters(text)",
        ref="""def final_letters(text):
    out = ""
    for word in text.split(" "):
        if word:
            out += word[-1].lower()
    return out
""",
        cases=[
            ("good morning",),
            ("one small step for man",),
            ("",),
            ("x",),
            ("HELLO WORLD",),
            ("jean-luc picard",),
            ("Neil Alden Armstrong",),
            ("big red dog",),
        ],
    ),
    dict(
        id="c09", pool="C", d=0.0, title="Lowest stock",
        prompt="stock maps item names to integer counts. Return the item with the smallest count; if several share it, return the alphabetically first of them (plain string comparison). Return None for an empty dict.",
        sig="lowest_stock(stock)",
        ref="""def lowest_stock(stock):
    if not stock:
        return None
    fewest = min(stock.values())
    return min(item for item, n in stock.items() if n == fewest)
""",
        cases=[
            ({"nuts": 40, "bolts": 25, "gears": 31},),
            ({"pins": 8, "clips": 3},),
            ({},),
            ({"only": -2},),
            ({"tape": 6, "glue": 6, "wire": 6},),
            ({"a": -1, "b": -3},),
            ({"cog": 9, "hub": 4, "fan": 4, "rod": 12},),
            ({"p": 0, "q": 0},),
        ],
    ),
    dict(
        id="c10", pool="C", d=0.4, title="Rank players",
        prompt="players is a list of [name, points] pairs. Return a list of the names ordered by points from highest to lowest; players with equal points are ordered alphabetically by name (a to z). Duplicates are kept.",
        sig="rank_players(players)",
        ref="""def rank_players(players):
    ordered = sorted(players, key=lambda p: (-p[1], p[0]))
    return [p[0] for p in ordered]
""",
        cases=[
            ([["ann", 5], ["bob", 9], ["cy", 7]],),
            ([["al", 2], ["bo", 8]],),
            ([],),
            ([["x", 1]],),
            ([["jo", 4], ["jo", 4], ["al", 1]],),
            ([["dan", 5], ["cat", 5], ["ann", 5]],),
            ([["a", 3], ["b", -2], ["c", 10], ["d", 0]],),
            ([["pat", 4], ["eve", 4], ["sam", 9], ["lee", 1], ["kim", 4], ["tom", 9]],),
        ],
    ),
    dict(
        id="c11", pool="C", d=0.8, title="Expand repeats",
        prompt="spec is comma-separated items, each either a lowercase word like 'ab' or a repeat like 'ab*3' (the word repeated 3 times; the count may be 0). Return the list of words in the order written, with repeats expanded; the empty string gives []. There are no spaces.",
        sig="expand_repeats(spec)",
        ref="""def expand_repeats(spec):
    out = []
    if spec == "":
        return out
    for item in spec.split(","):
        if "*" in item:
            word, count = item.split("*")
            for _ in range(int(count)):
                out.append(word)
        else:
            out.append(item)
    return out
""",
        cases=[
            ("a*3,b",),
            ("x,y",),
            ("",),
            ("z*1",),
            ("m*0,n",),
            ("k*10,j",),
            ("ab*2,c",),
            ("w,w*2",),
        ],
    ),
    dict(
        id="c12", pool="C", d=1.2, title="Longest within budget",
        prompt="costs is a list of non-negative integers. Return the length of the longest contiguous sublist whose sum is at most budget; return 0 if no element fits (or the list is empty).",
        sig="longest_within_budget(costs, budget)",
        ref="""def longest_within_budget(costs, budget):
    best = 0
    start = 0
    total = 0
    for end, c in enumerate(costs):
        total += c
        while total > budget and start <= end:
            total -= costs[start]
            start += 1
        best = max(best, end - start + 1)
    return best
""",
        cases=[
            ([2, 1, 3, 1, 1], 5),
            ([1, 1, 1, 1], 1),
            ([3, 1, 2, 5, 1, 1, 4], 6),
            ([], 5),
            ([3], 5),
            ([4, 4], 3),
            ([0, 0, 1], 0),
            ([1, 2, 3], 10),
            ([5, 1, 1, 5, 2, 2, 2], 6),
        ],
    ),
]

"""Placeholder exercise bank (42 items) for the pilot.

Expected outputs are computed from the reference solutions, so the tests cannot disagree with them.
Difficulties are my guesses on the model's latent scale and MUST be re-estimated (IRT) from pilot data
before they are trusted. Pools: A = baseline anchors (10), B = mid assessment (6), C = post assessment (6),
P = practice (20). B and C are built as matched pairs. The bank is far too small for a multi-week study.
"""
import json
from dataclasses import dataclass

_EXPECTED = {}


@dataclass(frozen=True)
class Exercise:
    id: str
    pool: str       # "A", "B", "C" or "P"
    d: float        # difficulty on the same scale as the skill model (guess; calibrate before use)
    title: str
    prompt: str
    fname: str
    params: str
    ref: str        # reference solution: never sent to a client or to the AI helper
    cases: tuple    # argument tuples; the first two are shown to the learner as examples

    @property
    def starter(self):
        return f"def {self.fname}({self.params}):\n    pass\n"

    def expected(self):
        if self.id not in _EXPECTED:
            ns = {}
            exec(self.ref, ns)
            f = ns[self.fname]
            _EXPECTED[self.id] = [json.loads(json.dumps(f(*c))) for c in self.cases]
        return _EXPECTED[self.id]

    def examples(self):
        return [dict(call=f"{self.fname}({', '.join(repr(a) for a in c)})", expected=json.dumps(e))
                for c, e in zip(self.cases[:2], self.expected()[:2])]


def _ex(id, pool, d, title, prompt, sig, ref, cases):
    fname, params = sig.split("(", 1)
    return Exercise(id, pool, d, title, prompt, fname, params.rstrip(")"), ref.strip("\n") + "\n", tuple(cases))


ALL = [
    # ---- P: practice -------------------------------------------------------------------------------
    _ex("p01", "P", -1.2, "Sum of evens", "Return the sum of the even numbers in xs.", "even_sum(xs)",
        "def even_sum(xs):\n    return sum(x for x in xs if x % 2 == 0)",
        [([1, 2, 3, 4],), ([],), ([7, 9],), ([2, 2, 2],), ([-2, 5, -4],), ([10],)]),
    _ex("p02", "P", -1.1, "Count vowels", "Return how many vowels (a, e, i, o, u, either case) s contains.", "count_vowels(s)",
        "def count_vowels(s):\n    return sum(1 for c in s if c.lower() in 'aeiou')",
        [("hello",), ("",), ("RHYTHM",), ("AEIOUaeiou",), ("Programming is fun",)]),
    _ex("p03", "P", -1.0, "Clamp", "Return x limited to the range lo..hi (lo if x < lo, hi if x > hi).", "clamp(x, lo, hi)",
        "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))",
        [(5, 0, 10), (-3, 0, 10), (42, 0, 10), (0, 0, 0), (7, 7, 9), (1.5, 1, 2)]),
    _ex("p04", "P", -0.9, "Reverse words", "Return the words of s in reverse order, joined by single spaces.", "reverse_words(s)",
        "def reverse_words(s):\n    return ' '.join(s.split()[::-1])",
        [("hello world",), ("a",), ("",), ("  many   spaces here ",), ("one two three four",)]),
    _ex("p05", "P", -0.6, "Second largest",
        "Return the second largest distinct value in xs, or None if there are fewer than two distinct values.",
        "second_largest(xs)",
        "def second_largest(xs):\n    vals = sorted(set(xs))\n    return vals[-2] if len(vals) >= 2 else None",
        [([3, 1, 2],), ([5, 5, 5],), ([],), ([1, 2],), ([9, 9, 8, 8, 7],), ([-1, -5],)]),
    _ex("p06", "P", -0.6, "Palindrome",
        "Return True if s reads the same forwards and backwards, ignoring case and every character that is not a letter or digit.",
        "is_palindrome(s)",
        "def is_palindrome(s):\n    t = [c.lower() for c in s if c.isalnum()]\n    return t == t[::-1]",
        [("A man, a plan, a canal: Panama",), ("hello",), ("",), ("No lemon, no melon",), ("ab",), ("12321",)]),
    _ex("p07", "P", -0.5, "FizzBuzz list",
        "Return a list for 1..n: 'FizzBuzz' if divisible by 15, 'Fizz' if by 3, 'Buzz' if by 5, otherwise the number as a string.",
        "fizzbuzz_list(n)",
        "def fizzbuzz_list(n):\n    out = []\n    for i in range(1, n + 1):\n"
        "        out.append('FizzBuzz' if i % 15 == 0 else 'Fizz' if i % 3 == 0 else 'Buzz' if i % 5 == 0 else str(i))\n    return out",
        [(5,), (15,), (0,), (1,), (20,)]),
    _ex("p08", "P", -0.3, "Word frequency",
        "Return a dict mapping each lowercase word in s (split on whitespace) to the number of times it appears.",
        "word_freq(s)",
        "def word_freq(s):\n    out = {}\n    for w in s.lower().split():\n        out[w] = out.get(w, 0) + 1\n    return out",
        [("the cat and the hat",), ("",), ("Go go GO",), ("a b a b a",)]),
    _ex("p09", "P", -0.2, "Flatten one level",
        "xs holds ints and lists of ints. Return one flat list (one level of nesting only), keeping the order.",
        "flatten(xs)",
        "def flatten(xs):\n    out = []\n    for x in xs:\n        if isinstance(x, list):\n            out.extend(x)\n"
        "        else:\n            out.append(x)\n    return out",
        [([1, [2, 3], 4],), ([],), ([[1], [2], [3]],), ([[], 5],), ([1, 2],)]),
    _ex("p10", "P", -0.1, "Deduplicate",
        "Remove duplicates from xs, keeping the first occurrence of each value and the original order.",
        "dedupe_keep_order(xs)",
        "def dedupe_keep_order(xs):\n    seen, out = set(), []\n    for x in xs:\n        if x not in seen:\n"
        "            seen.add(x)\n            out.append(x)\n    return out",
        [([1, 2, 1, 3, 2],), ([],), (["a", "b", "a"],), ([5, 5, 5],), ([3, 2, 1],)]),
    _ex("p11", "P", 0.0, "Rotate left",
        "Rotate the list xs left by k positions (k may exceed len(xs)); return a new list.", "rotate_left(xs, k)",
        "def rotate_left(xs, k):\n    if not xs:\n        return []\n    k %= len(xs)\n    return xs[k:] + xs[:k]",
        [([1, 2, 3, 4, 5], 2), ([1, 2, 3], 0), ([], 3), ([1, 2, 3], 7), ([1], 5), ([1, 2, 3, 4], 4)]),
    _ex("p12", "P", 0.1, "Common prefix",
        "Return the longest common prefix of all strings in strs ('' if there is none or strs is empty).",
        "longest_common_prefix(strs)",
        "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    p = strs[0]\n    for s in strs[1:]:\n"
        "        while not s.startswith(p):\n            p = p[:-1]\n    return p",
        [(["flower", "flow", "flight"],), (["dog", "car"],), ([],), (["same", "same"],), (["a"],), (["ab", "abc", ""],)]),
    _ex("p13", "P", 0.2, "Anagram groups",
        "Group words that are anagrams of each other. Return a list of groups; sort each group alphabetically and sort the groups by their first word.",
        "anagram_groups(words)",
        "def anagram_groups(words):\n    groups = {}\n    for w in words:\n        groups.setdefault(''.join(sorted(w)), []).append(w)\n"
        "    return sorted(sorted(g) for g in groups.values())",
        [(["eat", "tea", "tan", "ate", "nat", "bat"],), ([],), (["a"],), (["ab", "ba", "abc"],), (["x", "x"],)]),
    _ex("p14", "P", 0.3, "Balanced brackets",
        "Return True if the brackets ()[]{} in s are balanced and correctly nested; ignore every other character.",
        "balanced(s)",
        "def balanced(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for c in s:\n        if c in '([{':\n"
        "            stack.append(c)\n        elif c in pairs:\n            if not stack or stack.pop() != pairs[c]:\n"
        "                return False\n    return not stack",
        [("([]{})",), ("(]",), ("",), ("((",), ("a(b)c",), ("{[}]",), (")(",)]),
    _ex("p15", "P", 0.4, "Two sum indices",
        "Return the pair (i, j) with i < j and nums[i] + nums[j] == target. If several pairs work, return the one with the smallest i, then the smallest j. Return None if there is none.",
        "two_sum_indices(nums, target)",
        "def two_sum_indices(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n"
        "            if nums[i] + nums[j] == target:\n                return (i, j)\n    return None",
        [([2, 7, 11, 15], 9), ([3, 2, 4], 6), ([1, 2], 10), ([], 0), ([3, 3], 6), ([1, 5, 1, 5], 6)]),
    _ex("p16", "P", 0.5, "Roman numerals",
        "Convert a Roman numeral (I V X L C D M, standard subtractive forms such as IV and CM) to an integer.",
        "roman_to_int(s)",
        "def roman_to_int(s):\n    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n    total = 0\n"
        "    for i, c in enumerate(s):\n        if i + 1 < len(s) and vals[c] < vals[s[i + 1]]:\n            total -= vals[c]\n"
        "        else:\n            total += vals[c]\n    return total",
        [("III",), ("IV",), ("IX",), ("LVIII",), ("MCMXCIV",), ("XL",)]),
    _ex("p17", "P", 0.6, "Merge intervals",
        "Merge overlapping intervals (touching ones such as [1,2] and [2,3] also merge). Input is a list of [start, end]; return a sorted list of merged [start, end] lists.",
        "merge_intervals(intervals)",
        "def merge_intervals(intervals):\n    out = []\n    for a, b in sorted(intervals):\n        if out and a <= out[-1][1]:\n"
        "            out[-1][1] = max(out[-1][1], b)\n        else:\n            out.append([a, b])\n    return out",
        [([[1, 3], [2, 6], [8, 10], [15, 18]],), ([[1, 4], [4, 5]],), ([],), ([[1, 2]],), ([[5, 6], [1, 3], [2, 4]],), ([[1, 10], [2, 3]],)]),
    _ex("p18", "P", 0.7, "Run-length encode",
        "Run-length encode s: each run of the same character becomes the character followed by the run length, e.g. 'aaabcc' -> 'a3b1c2'.",
        "compress(s)",
        "def compress(s):\n    out = []\n    i = 0\n    while i < len(s):\n        j = i\n        while j < len(s) and s[j] == s[i]:\n"
        "            j += 1\n        out.append(f'{s[i]}{j - i}')\n        i = j\n    return ''.join(out)",
        [("aaabcc",), ("",), ("a",), ("abc",), ("zzzzzzzzzzzz",), ("aabbaa",)]),
    _ex("p19", "P", 0.9, "Spiral order",
        "Return the elements of a rectangular matrix (list of rows) in clockwise spiral order, starting at the top-left.",
        "spiral_order(matrix)",
        "def spiral_order(matrix):\n    out = []\n    m = [row[:] for row in matrix]\n    while m:\n        out.extend(m.pop(0))\n"
        "        m = [list(r) for r in zip(*m)][::-1]\n    return out",
        [([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), ([[1, 2, 3, 4]],), ([[1], [2], [3]],), ([],), ([[1, 2], [3, 4]],), ([[1, 2, 3], [4, 5, 6]],)]),
    _ex("p20", "P", 1.1, "Longest increasing subsequence",
        "Return the length of the longest strictly increasing subsequence of xs (the elements need not be adjacent).",
        "lis_length(xs)",
        "def lis_length(xs):\n    best = [1] * len(xs)\n    for i in range(len(xs)):\n        for j in range(i):\n"
        "            if xs[j] < xs[i]:\n                best[i] = max(best[i], best[j] + 1)\n    return max(best, default=0)",
        [([10, 9, 2, 5, 3, 7, 101, 18],), ([],), ([1],), ([5, 4, 3],), ([1, 2, 3, 4],), ([0, 1, 0, 3, 2, 3],), ([7, 7, 7],)]),
    # ---- A: baseline anchors -----------------------------------------------------------------------
    _ex("a01", "A", -1.3, "Product", "Return the product of all numbers in xs (1 for an empty list).", "product(xs)",
        "def product(xs):\n    p = 1\n    for x in xs:\n        p *= x\n    return p",
        [([2, 3, 4],), ([],), ([5],), ([-1, 2],), ([0, 9],)]),
    _ex("a02", "A", -1.1, "Count a character", "Return how many times the single character ch appears in s.", "count_char(s, ch)",
        "def count_char(s, ch):\n    return s.count(ch)",
        [("banana", "a"), ("", "x"), ("hello", "z"), ("aaa", "a"), ("Mississippi", "s")]),
    _ex("a03", "A", -0.8, "Spread", "Return the largest minus the smallest number in xs (0 if xs is empty).", "max_diff(xs)",
        "def max_diff(xs):\n    return max(xs) - min(xs) if xs else 0",
        [([1, 5, 3],), ([],), ([4],), ([-2, 8],), ([7, 7],)]),
    _ex("a04", "A", -0.6, "Capitalise words",
        "Return s with each word capitalised (first letter upper, rest lower), words separated by single spaces.",
        "capitalize_words(s)",
        "def capitalize_words(s):\n    return ' '.join(w.capitalize() for w in s.split())",
        [("hello world",), ("",), ("PYTHON is FUN",), ("  a  b ",), ("x",)]),
    _ex("a05", "A", -0.3, "Is sorted", "Return True if xs is in non-decreasing order.", "is_sorted(xs)",
        "def is_sorted(xs):\n    return all(a <= b for a, b in zip(xs, xs[1:]))",
        [([1, 2, 2, 3],), ([],), ([3, 1],), ([5],), ([1, 3, 2],)]),
    _ex("a06", "A", -0.1, "Digit sum", "Return the sum of the decimal digits of the integer n (ignore the sign).", "digit_sum(n)",
        "def digit_sum(n):\n    return sum(int(c) for c in str(abs(n)))",
        [(123,), (0,), (-45,), (1000,), (99999,)]),
    _ex("a07", "A", 0.2, "Common elements", "Return the sorted list of distinct values that appear in both lists.", "common_elements(a, b)",
        "def common_elements(a, b):\n    return sorted(set(a) & set(b))",
        [([1, 2, 2, 3], [2, 3, 4]), ([], [1]), ([1], [2]), ([5, 5], [5]), (["b", "a"], ["a", "c"])]),
    _ex("a08", "A", 0.4, "Most common character",
        "Return the most frequent character of s, ignoring spaces; on a tie return the alphabetically smallest; return None if there is no non-space character.",
        "most_common_char(s)",
        "def most_common_char(s):\n    counts = {}\n    for ch in s:\n        if ch != ' ':\n            counts[ch] = counts.get(ch, 0) + 1\n"
        "    if not counts:\n        return None\n    top = max(counts.values())\n    return min(ch for ch, n in counts.items() if n == top)",
        [("hello world",), ("",), ("   ",), ("abab",), ("zzzy",), ("Aa",)]),
    _ex("a09", "A", 0.7, "Pascal row", "Return row n (row 0 is [1]) of Pascal's triangle as a list.", "pascal_row(n)",
        "def pascal_row(n):\n    row = [1]\n    for _ in range(n):\n        row = [1] + [a + b for a, b in zip(row, row[1:])] + [1]\n    return row",
        [(0,), (1,), (2,), (5,), (8,)]),
    _ex("a10", "A", 1.0, "Valid IPv4",
        "Return True if s is a valid IPv4 address: four dot-separated parts, each a whole number 0-255 written without leading zeros (except '0' itself).",
        "valid_ipv4(s)",
        "def valid_ipv4(s):\n    parts = s.split('.')\n    if len(parts) != 4:\n        return False\n    for p in parts:\n"
        "        if not p.isdigit() or (len(p) > 1 and p[0] == '0') or int(p) > 255:\n            return False\n    return True",
        [("192.168.1.1",), ("256.1.1.1",), ("1.2.3",), ("01.2.3.4",), ("0.0.0.0",), ("a.b.c.d",), ("1.2.3.4.5",), ("",)]),
    # ---- B: mid assessment (matched with C) --------------------------------------------------------
    _ex("b01", "B", -0.9, "Sum of squares", "Return 1² + 2² + ... + n² (0 if n < 1).", "sum_of_squares(n)",
        "def sum_of_squares(n):\n    return sum(i * i for i in range(1, n + 1))", [(3,), (0,), (1,), (10,), (-2,)]),
    _ex("b02", "B", -0.4, "Capitalised words", "Return how many words in s start with an uppercase letter.", "count_capitalised(s)",
        "def count_capitalised(s):\n    return sum(1 for w in s.split() if w[0].isupper())",
        [("Hello big World",), ("",), ("all lower",), ("A B C",), ("x Y z",)]),
    _ex("b03", "B", 0.0, "Running total", "Return a list whose element i is the sum of xs[0..i].", "running_total(xs)",
        "def running_total(xs):\n    out, total = [], 0\n    for x in xs:\n        total += x\n        out.append(total)\n    return out",
        [([1, 2, 3, 4],), ([],), ([5],), ([-1, 1, -1],), ([0, 0],)]),
    _ex("b04", "B", 0.3, "Group by length",
        "Return a dict mapping each word length to the alphabetically sorted list of words with that length.", "group_by_length(words)",
        "def group_by_length(words):\n    out = {}\n    for w in words:\n        out.setdefault(len(w), []).append(w)\n"
        "    return {k: sorted(v) for k, v in out.items()}",
        [(["a", "bb", "cc", "d", "eee"],), ([],), (["hi", "hi"],), (["zeta", "beta", "alpha"],)]),
    _ex("b05", "B", 0.7, "Transpose", "Return the transpose of a rectangular matrix (list of rows) as a list of rows ([] stays []).", "transpose(m)",
        "def transpose(m):\n    return [list(r) for r in zip(*m)]",
        [([[1, 2, 3], [4, 5, 6]],), ([[1]],), ([],), ([[1, 2], [3, 4], [5, 6]],), ([[7, 8, 9]],)]),
    _ex("b06", "B", 1.0, "Smallest window sum",
        "Return the smallest sum of any k consecutive elements of xs; return None if k < 1 or k > len(xs).", "min_window_sum(xs, k)",
        "def min_window_sum(xs, k):\n    if k < 1 or k > len(xs):\n        return None\n    return min(sum(xs[i:i + k]) for i in range(len(xs) - k + 1))",
        [([4, 2, 1, 7, 3], 2), ([1, 2, 3], 3), ([1, 2], 3), ([5], 1), ([3, -1, -2, 4], 2), ([1, 2, 3], 0)]),
    # ---- C: post assessment (matched with B) -------------------------------------------------------
    _ex("c01", "C", -0.9, "Sum of cubes", "Return 1³ + 2³ + ... + n³ (0 if n < 1).", "sum_of_cubes(n)",
        "def sum_of_cubes(n):\n    return sum(i ** 3 for i in range(1, n + 1))", [(3,), (0,), (1,), (6,), (-4,)]),
    _ex("c02", "C", -0.4, "Long words", "Return how many words in s have more than n letters.", "count_long_words(s, n)",
        "def count_long_words(s, n):\n    return sum(1 for w in s.split() if len(w) > n)",
        [("the quick brown fox", 3), ("", 2), ("a bb ccc", 1), ("abc def", 3), ("longword", 0)]),
    _ex("c03", "C", 0.0, "Differences", "Return a list whose element i is xs[i+1] - xs[i] (empty if xs has fewer than two elements).", "differences(xs)",
        "def differences(xs):\n    return [b - a for a, b in zip(xs, xs[1:])]",
        [([1, 4, 9, 16],), ([],), ([5],), ([3, 1],), ([2, 2, 2],)]),
    _ex("c04", "C", 0.3, "Group by first letter",
        "Return a dict mapping each lowercase first letter to the alphabetically sorted list of words starting with it (grouping is case-insensitive; keep each word as given).",
        "group_by_first_letter(words)",
        "def group_by_first_letter(words):\n    out = {}\n    for w in words:\n        out.setdefault(w[0].lower(), []).append(w)\n"
        "    return {k: sorted(v) for k, v in out.items()}",
        [(["apple", "Avocado", "banana", "blueberry", "cherry"],), ([],), (["x"],), (["Zed", "zip", "able"],)]),
    _ex("c05", "C", 0.7, "Rotate matrix", "Rotate a square matrix (list of rows) 90 degrees clockwise and return the new matrix.", "rotate_clockwise(m)",
        "def rotate_clockwise(m):\n    return [list(r) for r in zip(*m[::-1])]",
        [([[1, 2], [3, 4]],), ([[1]],), ([],), ([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), ([[0, 1], [1, 0]],)]),
    _ex("c06", "C", 1.0, "Largest window sum",
        "Return the largest sum of any k consecutive elements of xs; return None if k < 1 or k > len(xs).", "max_window_sum(xs, k)",
        "def max_window_sum(xs, k):\n    if k < 1 or k > len(xs):\n        return None\n    return max(sum(xs[i:i + k]) for i in range(len(xs) - k + 1))",
        [([4, 2, 1, 7, 3], 2), ([1, 2, 3], 3), ([1, 2], 3), ([5], 1), ([-3, -1, -2, -4], 2), ([1, 2, 3], 0)]),
]

from .bank_ext import ITEMS as _EXT  # noqa: E402  (extra items, see bank_ext/)

ALL.extend(_ex(*t) for t in _EXT)
# Calibrated difficulties (from `python -m pilot.calibrate`) replace the nominal guesses when the file is present.
import os as _os  # noqa: E402
from dataclasses import replace as _replace  # noqa: E402

_CAL = _os.path.join(_os.path.dirname(__file__), "calibrated.json")
if _os.path.exists(_CAL):
    _items = json.load(open(_CAL))["items"]
    ALL[:] = [_replace(e, d=_items[e.id]) if e.id in _items else e for e in ALL]
BANK = {e.id: e for e in ALL}


def pool(name):
    return [e for e in ALL if e.pool == name]

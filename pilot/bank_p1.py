"""Practice-pool items p21..p58 (difficulty -1.3 .. +0.2)."""

ITEMS = [
    dict(id="p21", pool="P", d=-1.3, title="Last item",
         prompt="Return the last element of the list xs, or None if the list is empty.",
         sig="last_item(xs)",
         ref='''def last_item(xs):
    return xs[-1] if xs else None
''',
         cases=[([1, 2, 3],), (["a", "b"],), ([],), ([7],), ([None, 5, 0],), ([[1], [2, 3]],), ([-4, -9],)]),

    dict(id="p22", pool="P", d=-1.3, title="Shout it",
         prompt="Return s in uppercase followed by one exclamation mark. If s is the empty string, return the empty string.",
         sig="shout(s)",
         ref='''def shout(s):
    return s.upper() + "!" if s else ""
''',
         cases=[("hello",), ("Hi there",), ("",), ("a",), ("ALREADY",), ("x1y2",), ("  sp ",)]),

    dict(id="p23", pool="P", d=-1.2, title="Is odd",
         prompt="Return True if the integer n is odd and False otherwise. Negative numbers count too (-3 is odd).",
         sig="is_odd(n)",
         ref='''def is_odd(n):
    return n % 2 == 1
''',
         cases=[(3,), (4,), (0,), (-3,), (-8,), (1,), (100001,)]),

    dict(id="p24", pool="P", d=-1.2, title="Count negatives",
         prompt="Return how many numbers in the list xs are strictly less than zero. Zero is not negative.",
         sig="count_negatives(xs)",
         ref='''def count_negatives(xs):
    return sum(1 for x in xs if x < 0)
''',
         cases=[([1, -2, 3, -4],), ([5, 6],), ([],), ([-1],), ([0, -1, 0],), ([-5, -5, -5],), ([-1, 2, -3, 4, -5, 6],)]),

    dict(id="p25", pool="P", d=-1.1, title="Double everything",
         prompt="Return a new list in which every number of xs is doubled, keeping the same order.",
         sig="double_all(xs)",
         ref='''def double_all(xs):
    return [2 * x for x in xs]
''',
         cases=[([1, 2, 3],), ([0, -4],), ([],), ([5],), ([-1, -2, 3],), ([10, 10, 10],), ([100, 0, 7],)]),

    dict(id="p26", pool="P", d=-1.1, title="Total length",
         prompt="Return the total number of characters in all the strings of the list words added together. An empty list gives 0.",
         sig="total_length(words)",
         ref='''def total_length(words):
    return sum(len(w) for w in words)
''',
         cases=[(["ab", "cde"],), (["hello"],), ([],), (["", " "],), (["a", "", "bb", ""],), (["x", "x", "x", "x", "x"],), (["Hello", "World!"],)]),

    dict(id="p27", pool="P", d=-1.1, title="First word",
         prompt="Return the first word of the string s. Words are runs of non-whitespace characters separated by whitespace, and punctuation stays part of the word. Return an empty string if s has no words.",
         sig="first_word(s)",
         ref='''def first_word(s):
    parts = s.split()
    return parts[0] if parts else ""
''',
         cases=[("hello world",), ("one",), ("",), ("   ",), ("  leading space",), ("tab\tseparated",), ("Hello, world",)]),

    dict(id="p28", pool="P", d=-1.0, title="Keep positives",
         prompt="Return a new list containing only the numbers in xs that are greater than zero, in their original order.",
         sig="keep_positive(xs)",
         ref='''def keep_positive(xs):
    return [x for x in xs if x > 0]
''',
         cases=[([3, -1, 4, -1, 5],), ([-2, -3],), ([],), ([0, 1, 0],), ([7],), ([2, 2, -2, 2],), ([-1, 5, -1, 6, 0, 7],)]),

    dict(id="p29", pool="P", d=-1.0, title="Lookup with default",
         prompt="Return the value stored under key in the dictionary d. If key is not a key of d (keys must match exactly, including case), return default instead.",
         sig="lookup(d, key, default)",
         ref='''def lookup(d, key, default):
    if key in d:
        return d[key]
    return default
''',
         cases=[({"a": 1, "b": 2}, "a", 0), ({"a": 1}, "z", "none"), ({}, "x", -1), ({"x": None}, "x", "dflt"),
                ({"k": 0}, "k", 5), ({"a": [1, 2]}, "a", []), ({"A": 1}, "a", 9)]),

    dict(id="p30", pool="P", d=-0.9, title="Count capitals",
         prompt="Return how many characters of the string s are uppercase letters from A to Z. Digits, spaces and punctuation do not count.",
         sig="count_uppercase(s)",
         ref='''def count_uppercase(s):
    return sum(1 for c in s if "A" <= c <= "Z")
''',
         cases=[("Hello World",), ("abc",), ("",), ("ABC",), ("a1B2C3!",), ("camelCaseString",), ("X",)]),

    dict(id="p31", pool="P", d=-0.9, title="Sign list",
         prompt="Return a list with one entry per number in xs: 1 if the number is positive, -1 if it is negative, and 0 if it is zero. Keep the original order.",
         sig="sign_list(xs)",
         ref='''def sign_list(xs):
    return [1 if x > 0 else -1 if x < 0 else 0 for x in xs]
''',
         cases=[([5, -3, 0],), ([2, 4],), ([],), ([0],), ([-1, -1],), ([0, 0, 3, -8],), ([10, -10, 10],)]),

    dict(id="p32", pool="P", d=-0.9, title="Every other",
         prompt="Return a new list with the elements of xs at positions 0, 2, 4, and so on (the first element, then every second one after it).",
         sig="every_other(xs)",
         ref='''def every_other(xs):
    return xs[::2]
''',
         cases=[([1, 2, 3, 4, 5],), (["a", "b", "c", "d"],), ([],), ([9],), ([1, 2],), (["x", "y", "z"],), ([5, 6, 7, 8, 9, 10],)]),

    dict(id="p33", pool="P", d=-0.8, title="Strip digits",
         prompt="Return the string s with every digit character 0-9 removed. All other characters, including spaces, stay in their original order.",
         sig="strip_digits(s)",
         ref='''def strip_digits(s):
    return "".join(c for c in s if c not in "0123456789")
''',
         cases=[("a1b2c3",), ("abc",), ("",), ("12345",), ("R2-D2",), ("room 101 a",), ("x9",)]),

    dict(id="p34", pool="P", d=-0.8, title="Largest magnitude",
         prompt="Return the largest absolute value among the numbers in xs; the result is never negative. Return 0 for an empty list.",
         sig="max_abs(xs)",
         ref='''def max_abs(xs):
    return max((abs(x) for x in xs), default=0)
''',
         cases=[([1, -5, 3],), ([2, 4],), ([],), ([-7],), ([0, 0],), ([-3, 3],), ([-10, 9, 8],), ([4, -4, 2],)]),

    dict(id="p35", pool="P", d=-0.7, title="Count words",
         prompt="Return the number of words in the string s. A word is a group of non-space characters, and words are separated by one or more spaces. An empty or all-space string has 0 words.",
         sig="count_words(s)",
         ref='''def count_words(s):
    return len(s.split())
''',
         cases=[("the quick brown fox",), ("hello",), ("",), ("   ",), ("  two   spaces  ",), ("a b c d e f",), (" lead",)]),

    dict(id="p36", pool="P", d=-0.7, title="Repeat each",
         prompt="Return a string in which every character of s is repeated n times in place; for example 'ab' with n=2 gives 'aabb'. If n is 0 or s is empty the result is an empty string. Spaces are repeated like other characters.",
         sig="repeat_each(s, n)",
         ref='''def repeat_each(s, n):
    return "".join(c * n for c in s)
''',
         cases=[("abc", 2), ("xy", 3), ("", 4), ("a", 0), ("hi", 1), ("Go!", 2), ("z", 5), ("a b", 2)]),

    dict(id="p37", pool="P", d=-0.7, title="Initials",
         prompt="Return the first letter of each word in the string name, uppercased and joined with no separators. Words are separated by one or more spaces; return an empty string if name has no words.",
         sig="initials(name)",
         ref='''def initials(name):
    return "".join(w[0].upper() for w in name.split())
''',
         cases=[("john ronald tolkien",), ("ada lovelace",), ("",), ("madonna",), ("Grace  Hopper",), ("  ",), ("mary jane Watson",), ("x y",)]),

    dict(id="p38", pool="P", d=-0.6, title="Any duplicates",
         prompt="Return True if some value appears more than once in the list xs, and False otherwise. Values are equal only if they are exactly equal ('a' and 'A' differ).",
         sig="has_duplicates(xs)",
         ref='''def has_duplicates(xs):
    seen = []
    for x in xs:
        if x in seen:
            return True
        seen.append(x)
    return False
''',
         cases=[([1, 2, 3, 2],), ([1, 2, 3],), ([],), ([5],), ([4, 4],), (["a", "b", "A"],), ([0, 1, 0],), ([1, 2, 3, 4, 5, 6, 1],), ([-2, -2],)]),

    dict(id="p39", pool="P", d=-0.6, title="Zero padding",
         prompt="Return the non-negative integer n as a string, padded on the left with '0' characters until it is at least width characters long. If it is already that long or longer, return it unchanged.",
         sig="pad_number(n, width)",
         ref='''def pad_number(n, width):
    s = str(n)
    while len(s) < width:
        s = "0" + s
    return s
''',
         cases=[(7, 3), (42, 5), (123, 2), (0, 1), (0, 4), (1000, 4), (5, 1), (99, 6)]),

    dict(id="p40", pool="P", d=-0.5, title="Count in range",
         prompt="Count how many numbers x in the list xs satisfy lo <= x <= hi, where both ends are included. If lo is greater than hi the answer is 0.",
         sig="count_in_range(xs, lo, hi)",
         ref='''def count_in_range(xs, lo, hi):
    return sum(1 for x in xs if lo <= x <= hi)
''',
         cases=[([1, 5, 10, 15], 5, 10), ([1, 2, 3], 10, 20), ([], 0, 5), ([5], 5, 5), ([-3, -1, 0, 2], -2, 1),
                ([4, 4, 4], 4, 4), ([1, 2, 3], 3, 1), ([0, 10, 20, 30], 10, 30)]),

    dict(id="p41", pool="P", d=-0.5, title="Leap year",
         prompt="Return True if the integer year is a Gregorian leap year: it is divisible by 4, except that years divisible by 100 are not leap years unless they are also divisible by 400. Otherwise return False.",
         sig="leap_year(year)",
         ref='''def leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return year % 4 == 0
''',
         cases=[(2024,), (2023,), (1900,), (2000,), (2100,), (1996,), (2019,), (1600,)]),

    dict(id="p42", pool="P", d=-0.4, title="Middle character",
         prompt="Return the middle character of the string s if its length is odd, or the two middle characters if its length is even. For an empty string return an empty string.",
         sig="middle_char(s)",
         ref='''def middle_char(s):
    n = len(s)
    if n == 0:
        return ""
    if n % 2 == 1:
        return s[n // 2]
    return s[n // 2 - 1: n // 2 + 1]
''',
         cases=[("abcde",), ("abcd",), ("",), ("x",), ("ab",), ("racecar",), ("python",), ("12345678",)]),

    dict(id="p43", pool="P", d=-0.4, title="Sum of rows",
         prompt="rows is a list of lists of numbers. Return the sum of all the numbers in all the inner lists. Inner lists may be empty, and an empty outer list gives 0.",
         sig="sum_nested(rows)",
         ref='''def sum_nested(rows):
    total = 0
    for row in rows:
        for x in row:
            total += x
    return total
''',
         cases=[([[1, 2], [3, 4]],), ([[5], [6, 7, 8]],), ([],), ([[]],), ([[], [3], []],), ([[-5, 2], [-4]],), ([[10]],), ([[1, 1, 1], [2, 2, 2], [3]],)]),

    dict(id="p44", pool="P", d=-0.4, title="Index of max",
         prompt="Return the index of the largest value in the list xs. If the largest value occurs several times, return the index of its first occurrence. Return -1 for an empty list.",
         sig="index_of_max(xs)",
         ref='''def index_of_max(xs):
    if not xs:
        return -1
    best = 0
    for i in range(1, len(xs)):
        if xs[i] > xs[best]:
            best = i
    return best
''',
         cases=[([3, 9, 2],), ([5, 1, 5],), ([],), ([4],), ([-3, -1, -2],), ([1, 2, 3, 4, 5],), ([7, 7, 7],), ([2, 8, 8, 1],)]),

    dict(id="p45", pool="P", d=-0.3, title="Alternating case",
         prompt="Return s with the characters at even positions (0, 2, 4, ...) in uppercase and the characters at odd positions in lowercase. Spaces and punctuation occupy positions too, so they still advance the count.",
         sig="alternate_case(s)",
         ref='''def alternate_case(s):
    out = []
    for i, c in enumerate(s):
        out.append(c.upper() if i % 2 == 0 else c.lower())
    return "".join(out)
''',
         cases=[("hello",), ("abcd",), ("",), ("a",), ("HELLO world",), ("ab12 cd",), ("zZ",), ("MiXeD",)]),

    dict(id="p46", pool="P", d=-0.3, title="Longest word",
         prompt="Return the longest string in the list words. If several strings tie for the longest length, return the one that appears first. Return an empty string for an empty list.",
         sig="longest_word(words)",
         ref='''def longest_word(words):
    best = ""
    for w in words:
        if len(w) > len(best):
            best = w
    return best
''',
         cases=[(["a", "abc", "ab"],), (["cat", "dog", "bird"],), ([],), (["hi"],), (["aa", "bb", "cc"],), (["x", "", "yy", "zz"],), ([""],), (["Tree", "tree!", "house"],)]),

    dict(id="p47", pool="P", d=-0.2, title="Sort by length",
         prompt="Return a new list of the strings in words ordered from shortest to longest. Strings of equal length must keep the same relative order they had in words.",
         sig="sort_by_length(words)",
         ref='''def sort_by_length(words):
    return sorted(words, key=len)
''',
         cases=[(["ccc", "a", "bb"],), (["bb", "aa", "c"],), ([],), (["x"],), (["dd", "cc", "bb", "aa"],), (["abc", "", "ab", "a", ""],), (["Beta", "alpha", "Gamma", "pi"],)]),

    dict(id="p48", pool="P", d=-0.2, title="Invert dictionary",
         prompt="d is a dictionary mapping strings to strings, and no two keys share the same value. Return a new dictionary that maps each value of d to the key it came from. An empty dict gives an empty dict.",
         sig="invert_dict(d)",
         ref='''def invert_dict(d):
    out = {}
    for k, v in d.items():
        out[v] = k
    return out
''',
         cases=[({"a": "x", "b": "y"},), ({"one": "1"},), ({},), ({"A": "a", "a": "A"},), ({"k1": "v", "k2": "w", "k3": "u"},), ({"": "empty"},), ({"x": "x"},)]),

    dict(id="p49", pool="P", d=-0.2, title="Diagonal sum",
         prompt="grid is a square list of lists of numbers (n rows with n numbers each). Return the sum of the main diagonal: grid[0][0] + grid[1][1] + and so on. An empty grid gives 0.",
         sig="diagonal_sum(grid)",
         ref='''def diagonal_sum(grid):
    return sum(grid[i][i] for i in range(len(grid)))
''',
         cases=[([[1, 2], [3, 4]],), ([[5]],), ([],), ([[1, 0, 0], [0, 2, 0], [0, 0, 3]],), ([[-1, 5], [5, -1]],), ([[9, 8, 7], [6, 5, 4], [3, 2, 1]],), ([[0, 1], [1, 0]],)]),

    dict(id="p50", pool="P", d=-0.1, title="Format money",
         prompt="cents is a non-negative integer number of cents. Return it as a string made of a dollar sign, the whole dollars, a decimal point and exactly two digits of cents, for example 1234 gives '$12.34'. Do not add thousands separators.",
         sig="format_money(cents)",
         ref='''def format_money(cents):
    return "$" + str(cents // 100) + "." + str(cents % 100).rjust(2, "0")
''',
         cases=[(1234,), (5,), (0,), (100,), (99,), (100000,), (250,), (123456789,)]),

    dict(id="p51", pool="P", d=-0.1, title="Sum by name",
         prompt="pairs is a list of [name, amount] pairs. Return a dictionary mapping each distinct name to the sum of all its amounts. Names are case-sensitive, and an empty list gives an empty dict.",
         sig="sum_by_name(pairs)",
         ref='''def sum_by_name(pairs):
    totals = {}
    for name, amount in pairs:
        totals[name] = totals.get(name, 0) + amount
    return totals
''',
         cases=[([["a", 1], ["b", 2], ["a", 3]],), ([["x", 5]],), ([],), ([["a", -1], ["a", 1]],),
                ([["p", 2], ["q", 2], ["p", 2], ["q", -5]],), ([["A", 1], ["a", 2]],), ([["k", 0]],)]),

    dict(id="p52", pool="P", d=-0.1, title="Pangram check",
         prompt="Return True if the string s contains every letter from a to z at least once, ignoring uppercase versus lowercase. Characters that are not letters are ignored. Otherwise return False.",
         sig="is_pangram(s)",
         ref='''def is_pangram(s):
    letters = set(s.lower())
    for c in "abcdefghijklmnopqrstuvwxyz":
        if c not in letters:
            return False
    return True
''',
         cases=[("The quick brown fox jumps over the lazy dog",), ("hello world",), ("",), ("abcdefghijklmnopqrstuvwxyz",),
                ("abcdefghijklmnopqrstuvwxy",), ("Pack my box with five dozen liquor jugs!",), ("ABCDEFGHIJKLMNOPQRSTUVWXYZ",), ("a" * 30,)]),

    dict(id="p53", pool="P", d=0.0, title="Parse pairs",
         prompt="s holds comma-separated key=value pairs with no spaces, like 'a=1,b=22', where every value is an integer (possibly negative). Return a dict mapping each key to its int value; if a key repeats, the last value wins. An empty string gives an empty dict.",
         sig="parse_kv(s)",
         ref='''def parse_kv(s):
    out = {}
    if s == "":
        return out
    for part in s.split(","):
        key, value = part.split("=")
        out[key] = int(value)
    return out
''',
         cases=[("a=1,b=2",), ("x=10",), ("",), ("a=1,a=5",), ("k=-3,m=0",), ("one=1,two=2,three=3",), ("z=100,y=200,x=300",)]),

    dict(id="p54", pool="P", d=0.0, title="Top scorer",
         prompt="scores is a dictionary mapping names to numeric scores. Return the name with the highest score. If several names tie for the highest, return the one that comes first in ordinary string comparison (so 'Zed' comes before 'amy'). Return an empty string if scores is empty.",
         sig="top_scorer(scores)",
         ref='''def top_scorer(scores):
    if not scores:
        return ""
    best = max(scores.values())
    return min(name for name, score in scores.items() if score == best)
''',
         cases=[({"ann": 90, "bob": 85},), ({"x": 1, "y": 5, "z": 3},), ({},), ({"solo": 0},), ({"bob": 7, "amy": 7, "cy": 3},),
                ({"b": -1, "a": -1},), ({"Zed": 4, "amy": 4},)]),

    dict(id="p55", pool="P", d=0.0, title="Greatest common divisor",
         prompt="Return the greatest common divisor of the non-negative integers a and b. gcd_of(a, 0) is a, gcd_of(0, b) is b, and gcd_of(0, 0) is 0.",
         sig="gcd_of(a, b)",
         ref='''def gcd_of(a, b):
    while b != 0:
        a, b = b, a % b
    return a
''',
         cases=[(12, 18), (7, 13), (0, 5), (5, 0), (0, 0), (100, 75), (48, 48), (17, 34)]),

    dict(id="p56", pool="P", d=0.1, title="Prime test",
         prompt="Return True if the integer n is prime (greater than 1 and divisible only by 1 and itself), otherwise False. Zero, one and negative numbers are not prime.",
         sig="is_prime(n)",
         ref='''def is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True
''',
         cases=[(7,), (8,), (2,), (1,), (0,), (97,), (91,), (13,), (3,), (-5,), (89,)]),

    dict(id="p57", pool="P", d=0.1, title="Longest streak",
         prompt="flags is a list containing only 0 and 1. Return the length of the longest run of consecutive 1s. Return 0 if there are no 1s or the list is empty.",
         sig="longest_streak(flags)",
         ref='''def longest_streak(flags):
    best = 0
    run = 0
    for f in flags:
        if f == 1:
            run += 1
            if run > best:
                best = run
        else:
            run = 0
    return best
''',
         cases=[([1, 1, 0, 1],), ([0, 0],), ([],), ([1],), ([1, 0, 1, 1, 1, 0, 1, 1],), ([1, 1, 1, 1],), ([0, 1, 0, 1, 0],), ([1, 1, 0, 1, 1],)]),

    dict(id="p58", pool="P", d=0.2, title="Collatz steps",
         prompt="Starting from the positive integer n, repeat this rule until the number reaches 1: if it is even, halve it; if it is odd, multiply it by 3 and add 1. Return how many steps this takes (0 if n is already 1).",
         sig="collatz_steps(n)",
         ref='''def collatz_steps(n):
    steps = 0
    while n != 1:
        if n % 2 == 0:
            n //= 2
        else:
            n = 3 * n + 1
        steps += 1
    return steps
''',
         cases=[(6,), (1,), (7,), (2,), (3,), (27,), (16,), (12,)]),
]

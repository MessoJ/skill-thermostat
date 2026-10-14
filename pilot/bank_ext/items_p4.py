"""Practice items p97..p105 (pool P), one per difficulty from -1.0 to 1.3."""

ITEMS = [
    ("p97", "P", -1.0, "Count multiples",
     "n and k are positive integers. Return how many integers in the range 1..n (inclusive) are divisible by k, as an int. "
     "If n is smaller than k the answer is 0.",
     "count_multiples(n, k)",
     "def count_multiples(n, k):\n    return n // k",
     [(10, 3), (7, 7), (5, 10), (1, 1), (100, 7), (30, 5), (99, 100)]),

    ("p98", "P", -0.6, "Perfect square",
     "n is an integer (it may be negative). Return True if n is a perfect square (0, 1, 4, 9, 16, ...), otherwise False. "
     "Negative numbers are never perfect squares.",
     "is_square(n)",
     "import math\n\ndef is_square(n):\n    if n < 0:\n        return False\n    r = math.isqrt(n)\n    return r * r == n",
     [(16,), (15,), (0,), (1,), (-4,), (2,), (1000000,), (999999,)]),

    ("p99", "P", -0.3, "Seconds to clock",
     "secs is a non-negative integer number of seconds. Return a string 'H:MM:SS' where H is the whole number of hours "
     "(no leading zero, and not wrapped at 24, so 90000 seconds gives hours 25), and MM and SS are the minutes (0-59) and "
     "seconds (0-59), each zero-padded to two digits.",
     "seconds_to_clock(secs)",
     "def seconds_to_clock(secs):\n    h, rem = divmod(secs, 3600)\n    m, s = divmod(rem, 60)\n    return f'{h}:{m:02d}:{s:02d}'",
     [(65,), (3600,), (0,), (59,), (3661,), (86399,), (90000,), (360000,)]),

    ("p100", "P", 0.0, "Binary gap",
     "n is a positive integer. Look at its binary representation (no leading zeros) and return the length of the longest "
     "run of consecutive 0 bits that has a 1 bit on both sides, as an int. Return 0 if there is no such run "
     "(for example for 1, 8, or 7).",
     "binary_gap(n)",
     "def binary_gap(n):\n    best = 0\n    cur = 0\n    seen_one = False\n    for ch in bin(n)[2:]:\n"
     "        if ch == '1':\n            if seen_one:\n                best = max(best, cur)\n"
     "            seen_one = True\n            cur = 0\n        else:\n            cur += 1\n    return best",
     [(9,), (5,), (1,), (8,), (529,), (20,), (1041,), (15,), (32769,)]),

    ("p101", "P", 0.3, "Majority element",
     "xs is a list of integers. Return the value that appears strictly more than len(xs) / 2 times, or None if no "
     "value does (including when xs is empty).",
     "majority_element(xs)",
     "def majority_element(xs):\n    counts = {}\n    for x in xs:\n        counts[x] = counts.get(x, 0) + 1\n"
     "    for x, c in counts.items():\n        if c * 2 > len(xs):\n            return x\n    return None",
     [([3, 3, 4],), ([1, 2, 3],), ([],), ([7],), ([2, 2, 1, 1],), ([5, 1, 5, 1, 5],), ([-1, -1, -1, 2, 2],), ([4, 4, 4, 4],)]),

    ("p102", "P", 0.6, "Integer to Roman",
     "n is an integer from 1 to 3999. Return its Roman numeral as an uppercase string using the standard subtractive "
     "forms (IV = 4, IX = 9, XL = 40, XC = 90, CD = 400, CM = 900); for example 1994 is 'MCMXCIV'.",
     "int_to_roman(n)",
     "def int_to_roman(n):\n    table = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),\n"
     "             (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]\n"
     "    out = []\n    for v, sym in table:\n        while n >= v:\n            out.append(sym)\n            n -= v\n"
     "    return ''.join(out)",
     [(3,), (58,), (4,), (9,), (1994,), (3999,), (444,), (1,), (2024,)]),

    ("p103", "P", 0.9, "Days between dates",
     "a and b are dates given as strings 'YYYY-MM-DD' (valid Gregorian dates, years 1900 to 2100). Return the number of "
     "days from a to b as an int: positive if b is later than a, negative if b is earlier, 0 if they are the same day. "
     "A year is a leap year if it is divisible by 4, except years divisible by 100 that are not divisible by 400 "
     "(so 1900 and 2100 are not leap years and 2000 is).",
     "days_between(a, b)",
     "def days_between(a, b):\n    def leap(y):\n        return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)\n\n"
     "    def ordinal(s):\n        y, m, d = (int(p) for p in s.split('-'))\n"
     "        mdays = [31, 29 if leap(y) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n"
     "        total = sum(366 if leap(yy) else 365 for yy in range(1900, y))\n"
     "        return total + sum(mdays[:m - 1]) + d\n\n"
     "    return ordinal(b) - ordinal(a)",
     [("2024-01-01", "2024-01-31"), ("2024-03-01", "2024-03-01"), ("2024-03-10", "2024-03-01"),
      ("2023-12-31", "2024-01-01"), ("2024-02-28", "2024-03-01"), ("2023-02-28", "2023-03-01"),
      ("1900-02-28", "1900-03-01"), ("2000-02-28", "2000-03-01"), ("1999-01-01", "2001-01-01"),
      ("2100-01-01", "1900-01-01")]),

    ("p104", "P", 1.1, "Count partitions",
     "n is a non-negative integer. Return the number of ways to write n as a sum of positive integers where the order "
     "of the terms does not matter (so 3+1 and 1+3 count as the same way), as an int. The number itself counts as one "
     "way, and for n = 0 the answer is 1. For example n = 4 gives 5: 4, 3+1, 2+2, 2+1+1, 1+1+1+1.",
     "count_partitions(n)",
     "def count_partitions(n):\n    ways = [1] + [0] * n\n    for part in range(1, n + 1):\n"
     "        for total in range(part, n + 1):\n            ways[total] += ways[total - part]\n    return ways[n]",
     [(4,), (5,), (0,), (1,), (2,), (7,), (10,), (30,), (50,)]),

    ("p105", "P", 1.3, "Fewest jumps",
     "xs is a non-empty list of non-negative integers. You start at index 0; from index i you may jump forward to any "
     "index from i + 1 up to i + xs[i] (staying inside the list). Return the minimum number of jumps needed to reach "
     "the last index, as an int. Return 0 if the list has one element, and -1 if the last index cannot be reached.",
     "min_jumps(xs)",
     "def min_jumps(xs):\n    n = len(xs)\n    if n == 1:\n        return 0\n    jumps = 0\n    end = 0\n    far = 0\n"
     "    for i in range(n - 1):\n        far = max(far, i + xs[i])\n        if i == end:\n            if far <= i:\n"
     "                return -1\n            jumps += 1\n            end = far\n            if end >= n - 1:\n"
     "                return jumps\n    return jumps if end >= n - 1 else -1",
     [([2, 3, 1, 1, 4],), ([1, 1, 1],), ([5],), ([1, 0, 3],), ([0, 1],), ([3, 2, 1],), ([2, 3, 0, 1, 4],),
      ([1, 2, 3, 4, 5],), ([4, 1, 1, 3, 1, 1, 1],), ([1, 1, 0, 1],)]),
]

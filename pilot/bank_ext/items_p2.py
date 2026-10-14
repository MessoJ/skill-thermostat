"""Practice items p47..p72: lists, dicts, sets and numbers."""

ITEMS = [
    ("p47", "P", -1.3, "Count positives",
     "xs is a list of ints. Return how many of them are strictly greater than 0 (zero and negatives do not count). "
     "Return 0 for an empty list.",
     "count_positive(xs)",
     "def count_positive(xs):\n    return sum(1 for x in xs if x > 0)",
     [([3, -1, 4],), ([],), ([0, 0, -5],), ([1, 2, 3, 4],), ([-2, 0, 7, 0, 9, -1],), ([5],)]),

    ("p48", "P", -1.2, "Square each",
     "xs is a list of ints. Return a new list with the square of each element, in the same order. "
     "An empty list gives an empty list.",
     "square_all(xs)",
     "def square_all(xs):\n    return [x * x for x in xs]",
     [([1, 2, 3],), ([],), ([-4, 0, 5],), ([10],), ([-1, -1, 2],), ([7, -3, 0, 6],)]),

    ("p49", "P", -1.0, "Values above threshold",
     "d is a dict mapping strings to ints and k is an int. Return how many values in d are strictly greater than k. "
     "Return 0 for an empty dict.",
     "count_above(d, k)",
     "def count_above(d, k):\n    return sum(1 for v in d.values() if v > k)",
     [({"a": 1, "b": 5, "c": 9}, 4), ({}, 3), ({"x": 3, "y": 3}, 3), ({"x": 3, "y": 4}, 3),
      ({"a": -1, "b": -2}, -2), ({"a": 10, "b": 20, "c": 30, "d": 40}, 0), ({"a": 7}, 100)]),

    ("p50", "P", -0.9, "Merge two dicts",
     "a and b are dicts with string keys and int values. Return a new dict containing every key of a and of b. "
     "If a key appears in both, the value from b is used. Do not modify a or b.",
     "merge_dicts(a, b)",
     "def merge_dicts(a, b):\n    out = dict(a)\n    out.update(b)\n    return out",
     [({"x": 1}, {"y": 2}), ({}, {}), ({"x": 1, "y": 2}, {"y": 9}), ({"x": 1}, {}), ({}, {"k": 5}),
      ({"a": 1, "b": 2}, {"b": 3, "c": 4}), ({"a": 0}, {"a": 0})]),

    ("p51", "P", -0.7, "Row sums",
     "m is a matrix given as a list of rows, each row a list of ints (all rows have the same length). "
     "Return a list containing the sum of each row, in row order. Return [] if m has no rows.",
     "row_sums(m)",
     "def row_sums(m):\n    return [sum(r) for r in m]",
     [([[1, 2], [3, 4]],), ([],), ([[5]],), ([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), ([[-1, 1], [0, 0], [2, 2]],),
      ([[10, 20, 30]],)]),

    ("p52", "P", -0.6, "Diagonal sum",
     "m is a square matrix (a list of n rows, each a list of n ints). Return the sum of the main diagonal, i.e. the "
     "elements m[0][0], m[1][1], ..., m[n-1][n-1]. Return 0 if m is empty.",
     "diagonal_sum(m)",
     "def diagonal_sum(m):\n    return sum(m[i][i] for i in range(len(m)))",
     [([[1, 2], [3, 4]],), ([],), ([[7]],), ([[1, 0, 0], [0, 2, 0], [0, 0, 3]],), ([[1, 2, 3], [4, 5, 6], [7, 8, 9]],),
      ([[0, 9, 9], [9, -4, 9], [9, 9, 0]],)]),

    ("p53", "P", -0.5, "Count divisors",
     "n is an int with n >= 1. Return how many positive integers divide n exactly (including 1 and n itself).",
     "count_divisors(n)",
     "def count_divisors(n):\n    return sum(1 for i in range(1, n + 1) if n % i == 0)",
     [(6,), (1,), (7,), (12,), (36,), (100,), (97,)]),

    ("p54", "P", -0.4, "Sort by length then alphabet",
     "words is a list of lowercase strings. Return a new list sorted by length, shortest first. Words of equal length "
     "are ordered alphabetically (normal string comparison). Duplicates are kept.",
     "sort_by_length(words)",
     "def sort_by_length(words):\n    return sorted(words, key=lambda w: (len(w), w))",
     [(["bb", "a", "ccc"],), ([],), (["pear", "fig", "apple", "kiwi", "date"],), (["b", "a", "b", "a"],),
      (["zz", "aa", "z", "a"],), (["car", "cab", "ca", "cat"],)]),

    ("p55", "P", -0.2, "Is prime",
     "n is an int (possibly 0 or negative). Return True if n is a prime number and False otherwise. "
     "Numbers less than 2 are not prime.",
     "is_prime(n)",
     "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n    return True",
     [(7,), (10,), (2,), (1,), (0,), (-7,), (9,), (97,), (91,)]),

    ("p56", "P", -0.1, "GCD of a list",
     "xs is a list of non-negative ints. Return the greatest common divisor of all of them. "
     "gcd(0, x) is x, and the gcd of an empty list or of a list of only zeros is 0.",
     "gcd_all(xs)",
     "def gcd_all(xs):\n    g = 0\n    for x in xs:\n        a, b = g, x\n        while b:\n            a, b = b, a % b\n        g = a\n    return g",
     [([12, 18],), ([],), ([7],), ([0, 0],), ([0, 5],), ([8, 12, 20],), ([9, 28, 35],), ([100, 75, 50, 25],)]),

    ("p57", "P", 0.0, "Chunk a list",
     "xs is a list and k is an int with k >= 1. Split xs into consecutive chunks of length k, keeping the order. "
     "The last chunk may be shorter. Return the list of chunks (each a list); return [] for an empty xs.",
     "chunk(xs, k)",
     "def chunk(xs, k):\n    return [xs[i:i + k] for i in range(0, len(xs), k)]",
     [([1, 2, 3, 4], 2), ([], 3), ([1, 2, 3, 4, 5], 2), ([1, 2, 3], 1), ([1, 2, 3], 5), ([1, 2, 3, 4, 5, 6], 3),
      (["a", "b", "c", "d", "e", "f", "g"], 4)]),

    ("p58", "P", 0.1, "Interleave lists",
     "a and b are lists. Return a new list that alternates elements: a[0], b[0], a[1], b[1], ... When one list runs out, "
     "append all remaining elements of the other list in order.",
     "interleave(a, b)",
     "def interleave(a, b):\n    out = []\n    for i in range(max(len(a), len(b))):\n        if i < len(a):\n            out.append(a[i])\n        if i < len(b):\n            out.append(b[i])\n    return out",
     [([1, 2], [3, 4]), ([], []), ([1, 2, 3], [9]), ([1], [7, 8, 9]), ([], [4, 5]), (["a", "b"], ["x", "y", "z"]),
      ([1, 2, 3, 4], [])]),

    ("p59", "P", 0.2, "Merge counts",
     "a and b are dicts mapping strings to ints. Return a new dict with every key that appears in either. For a key "
     "in both, the value is the sum of the two values; otherwise it is the value from the dict that has it. "
     "Keep keys whose total is 0.",
     "merge_counts(a, b)",
     "def merge_counts(a, b):\n    out = dict(a)\n    for k, v in b.items():\n        out[k] = out.get(k, 0) + v\n    return out",
     [({"x": 1}, {"y": 2}), ({}, {}), ({"x": 1, "y": 2}, {"y": 3, "z": 4}), ({"a": 5}, {"a": -5}), ({"a": 2}, {}),
      ({}, {"b": 7}), ({"a": 1, "b": 2, "c": 3}, {"a": 10, "b": 20, "c": 30})]),

    ("p60", "P", 0.3, "To another base",
     "n is an int with n >= 0 and b is an int with 2 <= b <= 16. Return n written in base b as a string, using digits "
     "0-9 then lowercase a-f for values 10-15, with no prefix and no leading zeros. n = 0 gives '0'.",
     "to_base(n, b)",
     "def to_base(n, b):\n    if n == 0:\n        return '0'\n    digits = '0123456789abcdef'\n    out = []\n    while n:\n        out.append(digits[n % b])\n        n //= b\n    return ''.join(reversed(out))",
     [(5, 2), (0, 2), (255, 16), (255, 2), (10, 3), (100, 8), (4095, 16), (1, 7), (48879, 16)]),

    ("p61", "P", 0.45, "Invert a dict into groups",
     "d is a dict mapping string keys to string values. Return a dict mapping each distinct value of d to the list of "
     "all keys that have that value, with each list sorted alphabetically. Return {} for an empty d.",
     "group_keys_by_value(d)",
     "def group_keys_by_value(d):\n    out = {}\n    for k, v in d.items():\n        out.setdefault(v, []).append(k)\n    return {v: sorted(ks) for v, ks in out.items()}",
     [({"a": "x", "b": "y"},), ({},), ({"a": "x", "b": "x", "c": "y"},), ({"z": "q", "m": "q", "a": "q"},),
      ({"k": "v"},), ({"apple": "red", "cherry": "red", "banana": "yellow", "lemon": "yellow", "lime": "green"},)]),

    ("p62", "P", 0.6, "Sort by frequency",
     "xs is a list of ints. Return the distinct values of xs as a list, ordered by how often they occur (most frequent "
     "first). Values with the same count are ordered by value, smallest first. Return [] for an empty list.",
     "sort_by_frequency(xs)",
     "def sort_by_frequency(xs):\n    cnt = {}\n    for x in xs:\n        cnt[x] = cnt.get(x, 0) + 1\n    return sorted(cnt, key=lambda v: (-cnt[v], v))",
     [([1, 1, 2],), ([],), ([3, 1, 2],), ([5, 5, 5, 2, 2, 9],), ([4, 4, 3, 3],), ([-1, -1, 0, 0, 7],),
      ([2, 3, 3, 1, 1, 1, 2, 2, 2],)]),

    ("p63", "P", 0.7, "Count pairs with sum",
     "xs is a list of ints and target is an int. Count the pairs of positions (i, j) with i < j such that "
     "xs[i] + xs[j] == target. Equal values at different positions count as different pairs. Return the count.",
     "count_pairs(xs, target)",
     "def count_pairs(xs, target):\n    seen = {}\n    total = 0\n    for x in xs:\n        total += seen.get(target - x, 0)\n        seen[x] = seen.get(x, 0) + 1\n    return total",
     [([1, 2, 3, 4], 5), ([], 3), ([2, 2, 2], 4), ([1, 1], 3), ([3], 6), ([0, 0, 0, 0], 0), ([1, 5, 3, 3, 7, -1], 6),
      ([4, 4, 4, 4, 4], 8)]),

    ("p64", "P", 0.8, "Prime factors",
     "n is an int with n >= 1. Return the list of prime factors of n in ascending order, repeated according to "
     "multiplicity (so their product is n). For n = 1 return [].",
     "prime_factors(n)",
     "def prime_factors(n):\n    out = []\n    p = 2\n    while p * p <= n:\n        while n % p == 0:\n            out.append(p)\n            n //= p\n        p += 1\n    if n > 1:\n        out.append(n)\n    return out",
     [(12,), (1,), (7,), (60,), (97,), (64,), (1001,), (360,), (9973 * 2,)]),

    ("p65", "P", 0.9, "Zero out rows and columns",
     "m is a matrix given as a list of rows of ints (all rows have equal length; m may be empty). Return a new matrix of "
     "the same shape in which every cell is 0 if the original matrix has a 0 anywhere in that cell's row or column, "
     "and otherwise keeps its original value. Do not modify m.",
     "zero_cross(m)",
     "def zero_cross(m):\n    rows = {i for i, r in enumerate(m) if 0 in r}\n    cols = {j for r in m for j, v in enumerate(r) if v == 0}\n    return [[0 if i in rows or j in cols else v for j, v in enumerate(r)] for i, r in enumerate(m)]",
     [([[1, 2], [3, 0]],), ([],), ([[1, 2, 3], [4, 5, 6]],), ([[0, 1, 2], [3, 4, 5], [6, 7, 8]],),
      ([[1, 1, 1], [1, 0, 1], [1, 1, 1]],), ([[0]],), ([[1], [0], [2]],), ([[1, 2], [3, 4], [0, 5]],)]),

    ("p66", "P", 1.0, "Longest consecutive run of values",
     "xs is an unsorted list of ints that may contain duplicates. Return the length of the longest set of values in xs "
     "that form consecutive integers (such as 4, 5, 6, 7), regardless of their positions in xs. Duplicates are counted "
     "once. Return 0 for an empty list.",
     "longest_consecutive(xs)",
     "def longest_consecutive(xs):\n    s = set(xs)\n    best = 0\n    for x in s:\n        if x - 1 not in s:\n            y = x\n            while y + 1 in s:\n                y += 1\n            best = max(best, y - x + 1)\n    return best",
     [([100, 4, 200, 1, 3, 2],), ([],), ([5],), ([1, 1, 1],), ([1, 2, 2, 3],), ([10, 5, 12, 3, 55, 30, 4, 11, 2],),
      ([-2, -1, 0, 1, 7],), ([9, 1, 4, 7, 3, -1, 0, 5, 8, -1, 6],)]),

    ("p67", "P", 1.1, "Subarrays with given sum",
     "xs is a list of ints (which may be negative or zero) and k is an int. Count the contiguous, non-empty sub-lists "
     "xs[i:j] (i < j) whose elements add up to k. Sub-lists at different positions count separately even if equal. "
     "Return the count.",
     "count_subarrays(xs, k)",
     "def count_subarrays(xs, k):\n    seen = {0: 1}\n    pre = 0\n    total = 0\n    for x in xs:\n        pre += x\n        total += seen.get(pre - k, 0)\n        seen[pre] = seen.get(pre, 0) + 1\n    return total",
     [([1, 2, 3], 3), ([], 0), ([1, 1, 1], 2), ([0, 0, 0], 0), ([1, -1, 0], 0), ([3, 4, 7, 2, -3, 1, 4, 2], 7),
      ([5], 5), ([5], 4), ([-1, -1, 1], 0)]),

    ("p68", "P", 1.2, "Minimum coins",
     "coins is a list of distinct positive ints (unlimited supply of each) and amount is an int with amount >= 0. "
     "Return the smallest number of coins that add up to exactly amount, or -1 if that is impossible. "
     "amount = 0 needs 0 coins.",
     "min_coins(coins, amount)",
     "def min_coins(coins, amount):\n    INF = float('inf')\n    dp = [0] + [INF] * amount\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a and dp[a - c] + 1 < dp[a]:\n                dp[a] = dp[a - c] + 1\n    return -1 if dp[amount] == INF else dp[amount]",
     [([1, 2, 5], 11), ([2], 3), ([1], 0), ([5, 2], 0), ([1, 3, 4], 6), ([2, 5, 10], 27), ([7], 14), ([5, 10], 3),
      ([186, 419, 83, 408], 6249)]),

    ("p69", "P", 1.3, "Trapped rain water",
     "h is a list of non-negative ints giving the heights of bars of width 1 standing side by side. After rain, water "
     "collects between bars: above each bar it sits up to the lower of the tallest bar to its left and the tallest bar "
     "to its right (both including the bar itself), minus the bar's own height. Return the total units of water held. "
     "Return 0 if there are fewer than 3 bars.",
     "trap_water(h)",
     "def trap_water(h):\n    lo, hi = 0, len(h) - 1\n    lm = rm = 0\n    total = 0\n    while lo < hi:\n        if h[lo] < h[hi]:\n            lm = max(lm, h[lo])\n            total += lm - h[lo]\n            lo += 1\n        else:\n            rm = max(rm, h[hi])\n            total += rm - h[hi]\n            hi -= 1\n    return total",
     [([0, 1, 0, 2], ), ([],), ([3, 0, 3],), ([1, 2, 3],), ([2, 0, 2, 0, 2],), ([4, 2, 0, 3, 2, 5],),
      ([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1],), ([5, 4, 1, 2],), ([1, 0],)]),

    ("p70", "P", 1.3, "Next permutation",
     "xs is a list of ints (duplicates allowed). Consider all distinct orderings of the elements of xs sorted in "
     "lexicographic (dictionary) order, comparing lists element by element. Return the ordering that comes right after "
     "xs. If xs is already the last ordering (its elements are in non-increasing order), return the first one, i.e. "
     "the elements in ascending order. An empty list gives []. Do not modify xs.",
     "next_permutation(xs)",
     "def next_permutation(xs):\n    a = list(xs)\n    i = len(a) - 2\n    while i >= 0 and a[i] >= a[i + 1]:\n        i -= 1\n    if i < 0:\n        return sorted(a)\n    j = len(a) - 1\n    while a[j] <= a[i]:\n        j -= 1\n    a[i], a[j] = a[j], a[i]\n    a[i + 1:] = reversed(a[i + 1:])\n    return a",
     [([1, 2, 3],), ([],), ([3, 2, 1],), ([1, 1, 5],), ([1, 3, 2],), ([2, 3, 1],), ([5],), ([1, 5, 1],),
      ([2, 2, 1, 1],), ([1, 2, 4, 3, 2],)]),

    ("p71", "P", 0.1, "Reverse the digits",
     "n is an int (possibly negative or zero). Return the int whose decimal digits are those of n in reverse order, "
     "keeping the sign of n. Leading zeros created by the reversal vanish (120 becomes 21). 0 stays 0.",
     "reverse_int(n)",
     "def reverse_int(n):\n    r = int(str(abs(n))[::-1])\n    return -r if n < 0 else r",
     [(123,), (0,), (-456,), (120,), (7,), (1000,), (-90,), (98765,)]),

    ("p72", "P", 0.9, "Summarize ranges",
     "xs is a list of ints in strictly increasing order. Group it into maximal runs of consecutive integers (each "
     "value exactly 1 more than the previous). Return a list of strings, one per run in order: 'a->b' when the run "
     "goes from a to b (a < b), or just 'a' for a run of one value. Return [] for an empty list.",
     "summarize_ranges(xs)",
     "def summarize_ranges(xs):\n    out = []\n    i = 0\n    while i < len(xs):\n        j = i\n        while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:\n            j += 1\n        out.append(str(xs[i]) if i == j else f'{xs[i]}->{xs[j]}')\n        i = j + 1\n    return out",
     [([1, 2, 3, 7],), ([],), ([5],), ([1, 3, 5],), ([0, 1, 2, 4, 5, 7],), ([-2, -1, 0, 1],), ([1, 2, 4, 6, 7, 8, 10],),
      ([10, 11],)]),
]

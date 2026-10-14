"""Extension batch A: pool A anchors a11..a30 and matched B/C pairs b07..b12 / c07..c12."""

ITEMS = [
    # ---------------- Pool A: baseline anchors, d from -1.5 to +1.4 ----------------
    ("a11", "A", -1.5, "Double every number",
     "Given a list xs of integers, return a new list in which every number is doubled, in the same order. An empty list gives an empty list.",
     "double_all(xs)",
     "def double_all(xs):\n    return [2 * x for x in xs]\n",
     [([1, 2, 3],), ([],), ([0],), ([-4, 5],), ([10, 20, 30, 40],), ([7],)]),

    ("a12", "A", -1.35, "Starts with a vowel",
     "Given a string s, return True if its first character is one of a, e, i, o, u (lowercase or uppercase), otherwise False. The empty string gives False.",
     "starts_with_vowel(s)",
     "def starts_with_vowel(s):\n    return len(s) > 0 and s[0].lower() in 'aeiou'\n",
     [("apple",), ("banana",), ("",), ("Orange",), ("umbrella",), ("sky",), ("Zebra",), ("1abc",)]),

    ("a13", "A", -1.2, "Count the words",
     "Given a string s, return the number of words in it. Words are separated by one or more spaces, and there may be extra spaces at the start or the end. A string that is empty or has only spaces has 0 words.",
     "count_words(s)",
     "def count_words(s):\n    return len(s.split())\n",
     [("hello world",), ("one",), ("",), ("   ",), ("  a  b   c ",), ("the quick brown fox jumps",), ("  padded  ",)]),

    ("a14", "A", -1.05, "Letter grade",
     "Given an integer score from 0 to 100, return a one-letter grade as a string: 'A' for 90 or more, 'B' for 80 to 89, 'C' for 70 to 79, 'D' for 60 to 69, and 'F' for anything below 60.",
     "letter_grade(score)",
     "def letter_grade(score):\n    if score >= 90:\n        return 'A'\n    if score >= 80:\n        return 'B'\n    if score >= 70:\n        return 'C'\n    if score >= 60:\n        return 'D'\n    return 'F'\n",
     [(95,), (72,), (100,), (90,), (89,), (60,), (59,), (0,), (80,)]),

    ("a15", "A", -0.9, "Leap year",
     "Given a positive integer year, return True if it is a leap year and False otherwise. A year is a leap year if it is divisible by 4, except that years divisible by 100 are not leap years, unless they are also divisible by 400.",
     "is_leap_year(year)",
     "def is_leap_year(year):\n    if year % 400 == 0:\n        return True\n    if year % 100 == 0:\n        return False\n    return year % 4 == 0\n",
     [(2024,), (2023,), (1900,), (2000,), (2100,), (1996,), (1,), (400,)]),

    ("a16", "A", -0.75, "Strip the vowels",
     "Given a string s, return a new string with every vowel removed. The vowels are a, e, i, o, u in lowercase and uppercase. All other characters (consonants, digits, spaces, punctuation) stay in their original order.",
     "strip_vowels(s)",
     "def strip_vowels(s):\n    return ''.join(c for c in s if c.lower() not in 'aeiou')\n",
     [("hello",), ("sky",), ("",), ("AEIOU",), ("Programming is fun!",), ("rhythm 123",), ("Education",)]),

    ("a17", "A", -0.6, "Sum of large values",
     "Given a dict d that maps strings to integers and an integer t, return the sum of the values in d that are greater than or equal to t. If no value qualifies (or d is empty), return 0.",
     "sum_at_least(d, t)",
     "def sum_at_least(d, t):\n    total = 0\n    for v in d.values():\n        if v >= t:\n            total += v\n    return total\n",
     [({"a": 5, "b": 2, "c": 9}, 4), ({}, 3), ({"x": 1, "y": 2}, 10), ({"p": 3, "q": 3}, 3), ({"k": -5, "m": 7, "n": 0}, 0), ({"only": 8}, 8), ({"a": -2, "b": -3}, -3)]),

    ("a18", "A", -0.45, "Count one bits",
     "Given a non-negative integer n, return how many 1 digits appear in the binary representation of n. For n = 0 the answer is 0.",
     "count_one_bits(n)",
     "def count_one_bits(n):\n    count = 0\n    while n > 0:\n        count += n % 2\n        n //= 2\n    return count\n",
     [(5,), (0,), (1,), (7,), (8,), (255,), (1023,), (1024,), (170,)]),

    ("a19", "A", -0.3, "Fibonacci number",
     "Return the n-th Fibonacci number for an integer n from 0 to 30, where F(0) = 0, F(1) = 1, and every later number is the sum of the two before it (0, 1, 1, 2, 3, 5, 8, ...).",
     "fib(n)",
     "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
     [(6,), (10,), (0,), (1,), (2,), (15,), (20,), (30,)]),

    ("a20", "A", -0.15, "Sort words by length",
     "Given a list of lowercase words, return a new list sorted by length from shortest to longest. Words of the same length are ordered alphabetically (normal string order). Duplicates are kept.",
     "sort_by_length(words)",
     "def sort_by_length(words):\n    return sorted(words, key=lambda w: (len(w), w))\n",
     [(["pear", "fig", "apple"],), ([],), (["b", "a"],), (["cat", "bat", "ant", "zebra", "ox"],), (["hello", "hi", "hey", "hi"],), (["zz"],), (["dog", "cat", "bird", "ant", "eel"],)]),

    ("a21", "A", 0.0, "Count the primes",
     "Given an integer n >= 0, return how many prime numbers are less than or equal to n. A prime is an integer greater than 1 whose only positive divisors are 1 and itself.",
     "count_primes(n)",
     "def count_primes(n):\n    count = 0\n    for k in range(2, n + 1):\n        is_prime = True\n        d = 2\n        while d * d <= k:\n            if k % d == 0:\n                is_prime = False\n                break\n            d += 1\n        if is_prime:\n            count += 1\n    return count\n",
     [(10,), (0,), (1,), (2,), (3,), (30,), (97,), (100,), (200,)]),

    ("a22", "A", 0.15, "Deepest parentheses",
     "Given a string s whose round parentheses '(' and ')' are guaranteed to be balanced and properly nested, return the greatest nesting depth reached. Other characters are ignored. A string with no parentheses has depth 0.",
     "max_paren_depth(s)",
     "def max_paren_depth(s):\n    depth = 0\n    best = 0\n    for c in s:\n        if c == '(':\n            depth += 1\n            best = max(best, depth)\n        elif c == ')':\n            depth -= 1\n    return best\n",
     [("(a(b)c)",), ("()()",), ("((()))",), ("",), ("abc",), ("(()(()))",), ("(1+(2*(3+4)))-(5)",), ("()(()(())())",)]),

    ("a23", "A", 0.3, "Merge two sorted lists",
     "Given two lists a and b of integers, each already sorted in ascending order, return one new list containing all elements of both, in ascending order. Duplicates are kept.",
     "merge_sorted(a, b)",
     "def merge_sorted(a, b):\n    out = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            out.append(a[i])\n            i += 1\n        else:\n            out.append(b[j])\n            j += 1\n    out.extend(a[i:])\n    out.extend(b[j:])\n    return out\n",
     [([1, 3, 5], [2, 4, 6]), ([], []), ([1, 2], []), ([], [3, 4]), ([1, 1, 2], [1, 3]), ([5, 6, 7], [1, 2]), ([-3, 0, 4], [-5, -3, 9, 10]), ([2], [2])]),

    ("a24", "A", 0.45, "Pairs with a given sum",
     "Given a list xs of integers and an integer target, return how many pairs of positions i < j satisfy xs[i] + xs[j] == target. Equal values at different positions count as different pairs.",
     "count_pairs_with_sum(xs, target)",
     "def count_pairs_with_sum(xs, target):\n    count = 0\n    for i in range(len(xs)):\n        for j in range(i + 1, len(xs)):\n            if xs[i] + xs[j] == target:\n                count += 1\n    return count\n",
     [([1, 2, 3, 4], 5), ([], 3), ([1, 1, 1], 2), ([5], 10), ([2, 2, 3, 3], 5), ([0, 0, 0, 0], 0), ([-1, 1, 2, -2, 3], 1), ([4, 6], 11)]),

    ("a25", "A", 0.6, "Best single trade",
     "Given a list prices of non-negative integers, where prices[i] is a stock price on day i, you may buy on one day and sell on a strictly later day. Return the largest possible profit (sell price minus buy price). If no trade makes a profit, or there are fewer than two days, return 0.",
     "best_profit(prices)",
     "def best_profit(prices):\n    best = 0\n    lowest = None\n    for p in prices:\n        if lowest is not None and p - lowest > best:\n            best = p - lowest\n        if lowest is None or p < lowest:\n            lowest = p\n    return best\n",
     [([7, 1, 5, 3, 6, 4],), ([5, 4, 3],), ([],), ([2],), ([1, 2],), ([3, 3, 3],), ([9, 1, 2, 10, 0, 4],), ([2, 4, 1, 7, 3, 9],)]),

    ("a26", "A", 0.75, "Ways to climb stairs",
     "You climb a staircase of n steps (0 <= n <= 30), taking 1, 2 or 3 steps at a time. Return the number of different ordered sequences of moves that reach exactly step n. For n = 0 there is exactly 1 way (take no moves). For example n = 3 gives 4: 1+1+1, 1+2, 2+1, 3.",
     "stair_ways(n)",
     "def stair_ways(n):\n    ways = [0] * (n + 1)\n    ways[0] = 1\n    for i in range(1, n + 1):\n        for step in (1, 2, 3):\n            if i - step >= 0:\n                ways[i] += ways[i - step]\n    return ways[n]\n",
     [(3,), (1,), (0,), (2,), (4,), (5,), (10,), (20,), (30,)]),

    ("a27", "A", 0.9, "Postfix calculator",
     "Evaluate a postfix (reverse Polish) expression. tokens is a list of strings, each either an integer written in decimal (possibly negative, such as '-3') or one of the operators '+', '-', '*'. Read left to right: a number is pushed on a stack; an operator pops two values b (top) then a, and pushes a OP b (so '3', '4', '-' gives 3 - 4 = -1). The expression is always valid. Return the final integer.",
     "eval_rpn(tokens)",
     "def eval_rpn(tokens):\n    stack = []\n    for t in tokens:\n        if t in ('+', '-', '*'):\n            b = stack.pop()\n            a = stack.pop()\n            if t == '+':\n                stack.append(a + b)\n            elif t == '-':\n                stack.append(a - b)\n            else:\n                stack.append(a * b)\n        else:\n            stack.append(int(t))\n    return stack[0]\n",
     [(["2", "3", "+"],), (["4"],), (["5", "1", "2", "+", "4", "*", "+"],), (["3", "4", "-"],), (["-2", "3", "*"],), (["10", "2", "3", "*", "-"],), (["2", "3", "4", "*", "+", "5", "-"],), (["-7", "-3", "-"],)]),

    ("a28", "A", 1.05, "Count islands",
     "Given a grid (a list of equal-length lists) of 0s and 1s, count the islands. An island is a maximal group of 1-cells connected horizontally or vertically (diagonal neighbours are NOT connected). An empty grid, or one with no 1s, has 0 islands.",
     "count_islands(grid)",
     "def count_islands(grid):\n    seen = set()\n    count = 0\n    for r in range(len(grid)):\n        for c in range(len(grid[r])):\n            if grid[r][c] == 1 and (r, c) not in seen:\n                count += 1\n                stack = [(r, c)]\n                seen.add((r, c))\n                while stack:\n                    y, x = stack.pop()\n                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n                        ny, nx = y + dy, x + dx\n                        if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and grid[ny][nx] == 1 and (ny, nx) not in seen:\n                            seen.add((ny, nx))\n                            stack.append((ny, nx))\n    return count\n",
     [([[1, 0], [0, 1]],), ([],), ([[0, 0], [0, 0]],), ([[1, 1], [1, 1]],), ([[1, 1, 0, 0], [0, 1, 0, 1], [1, 0, 0, 1]],), ([[1]],), ([[1, 0, 1], [0, 1, 0], [1, 0, 1]],), ([[1, 1, 1], [0, 0, 1], [1, 1, 1]],)]),

    ("a29", "A", 1.2, "Fewest coins",
     "Given a list coins of distinct positive integer coin values (each may be used any number of times) and a non-negative integer amount, return the smallest number of coins that add up exactly to amount. For amount 0 return 0. If the amount cannot be made, return -1.",
     "min_coins(coins, amount)",
     "def min_coins(coins, amount):\n    INF = amount + 1\n    best = [0] + [INF] * amount\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a and best[a - c] + 1 < best[a]:\n                best[a] = best[a - c] + 1\n    return best[amount] if best[amount] != INF else -1\n",
     [([1, 2, 5], 11), ([2], 3), ([1], 0), ([1, 3, 4], 6), ([5, 2], 3), ([2, 5, 10, 1], 27), ([7], 14), ([4, 9], 17), ([186, 419, 83, 408], 6249)]),

    ("a30", "A", 1.4, "Edit distance",
     "Given two strings a and b, return the minimum number of single-character edits needed to turn a into b. One edit is an insertion of a character, a deletion of a character, or a substitution of one character by another. Either string may be empty.",
     "edit_distance(a, b)",
     "def edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i in range(1, len(a) + 1):\n        cur = [i] + [0] * len(b)\n        for j in range(1, len(b) + 1):\n            cost = 0 if a[i - 1] == b[j - 1] else 1\n            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)\n        prev = cur\n    return prev[len(b)]\n",
     [("cat", "cut"), ("", "abc"), ("abc", "abc"), ("kitten", "sitting"), ("flaw", "lawn"), ("intention", "execution"), ("a", ""), ("horse", "ros"), ("sunday", "saturday")]),

    # ---------------- Matched pairs for pools B and C ----------------
    # Pair 07 (d = -0.8): scan a string and count characters of one kind.
    ("b07", "B", -0.8, "Digit count",
     "Given a string s, return how many of its characters are decimal digits ('0' to '9'). Letters, spaces and punctuation do not count. The empty string gives 0.",
     "count_digits(s)",
     "def count_digits(s):\n    return sum(1 for c in s if c in '0123456789')\n",
     [("abc123",), ("",), ("no digits here",), ("2024-05-17",), ("a1b2c3d4e5",), ("007",), ("phone: 555 0199",)]),

    ("c07", "C", -0.8, "Capital letters",
     "Given a string text, return the number of capital letters in it, meaning the English letters 'A' to 'Z'. Lowercase letters, digits, spaces and punctuation are not counted. The empty string gives 0.",
     "count_capitals(text)",
     "def count_capitals(text):\n    n = 0\n    for ch in text:\n        if 'A' <= ch <= 'Z':\n            n += 1\n    return n\n",
     [("Hello World",), ("",), ("all lowercase",), ("ABC",), ("NASA and ESA",), ("Mixed CaSe 42!",), ("x",)]),

    # Pair 08 (d = -0.4): build a new list from a conditional rule on each element.
    ("b08", "B", -0.4, "Clip negatives",
     "Given a list xs of integers, return a new list of the same length in which every negative number is replaced by 0 and every other number is left unchanged. The original order is kept.",
     "clip_negatives(xs)",
     "def clip_negatives(xs):\n    return [x if x >= 0 else 0 for x in xs]\n",
     [([3, -1, 4],), ([],), ([-5, -6],), ([0, 2, 9],), ([-1, 5, -2, 8, 0],), ([7],), ([-100, 100],)]),

    ("c08", "C", -0.4, "Squares of odd numbers",
     "Given a list nums of integers, return a list containing the square of each odd number in nums, in the same order as they appear. Even numbers are skipped. Remember that negative odd numbers are odd too.",
     "odd_squares(nums)",
     "def odd_squares(nums):\n    return [n * n for n in nums if n % 2 != 0]\n",
     [([1, 2, 3, 4],), ([],), ([2, 4, 6],), ([5],), ([-3, 0, 7, -1],), ([9, 9, 2],), ([10, 11, 12, 13],)]),

    # Pair 09 (d = 0.0): accumulate into a dict.
    ("b09", "B", 0.0, "Totals per name",
     "Given a list rows where each row is a two-element list [name, amount] (a string and an integer), return a dict mapping each distinct name to the sum of all its amounts. An empty list gives an empty dict.",
     "totals_by_name(rows)",
     "def totals_by_name(rows):\n    out = {}\n    for name, amount in rows:\n        out[name] = out.get(name, 0) + amount\n    return out\n",
     [([["ann", 5], ["bob", 3], ["ann", 2]],), ([],), ([["zed", 10]],), ([["a", 1], ["a", 1], ["a", 1]],), ([["x", 4], ["y", -4], ["x", -4]],), ([["kim", 7], ["lee", 8], ["kim", 1], ["lee", 2], ["max", 0]],)]),

    ("c09", "C", 0.0, "Where each letter appears",
     "Given a string s, return a dict that maps each distinct character of s to the list of indices (positions, counting from 0) where that character occurs, in increasing order. The empty string gives an empty dict. Characters are compared exactly, so 'a' and 'A' are different keys.",
     "char_positions(s)",
     "def char_positions(s):\n    out = {}\n    for i, ch in enumerate(s):\n        out.setdefault(ch, []).append(i)\n    return out\n",
     [("abca",), ("",), ("z",), ("aaaa",), ("Aa",), ("banana",), ("a b a",)]),

    # Pair 10 (d = 0.3): scan with a comparison rule and handle ties / small inputs.
    ("b10", "B", 0.3, "Closest to the target",
     "Given a non-empty list xs of integers and an integer target, return the element of xs that is closest to target (smallest absolute difference). If two different values are equally close, return the smaller one.",
     "closest_to(xs, target)",
     "def closest_to(xs, target):\n    best = xs[0]\n    for x in xs[1:]:\n        if abs(x - target) < abs(best - target) or (abs(x - target) == abs(best - target) and x < best):\n            best = x\n    return best\n",
     [([1, 5, 9], 6), ([4], 100), ([2, 8], 5), ([10, 20, 30], 22), ([-5, -1, 3], 0), ([7, 3, 7], 7), ([1, 100, 50], 75), ([0, 4, -4], 1)]),

    ("c10", "C", 0.3, "Tightest pair",
     "Given a list nums of integers, return the smallest absolute difference between the values at any two different positions. Equal values at different positions give 0. If nums has fewer than two elements, return None.",
     "tightest_gap(nums)",
     "def tightest_gap(nums):\n    if len(nums) < 2:\n        return None\n    s = sorted(nums)\n    return min(s[i + 1] - s[i] for i in range(len(s) - 1))\n",
     [([1, 5, 3],), ([],), ([42],), ([10, 4, 7, 20],), ([5, 9, 5],), ([-3, 8, -2, 15],), ([100, 1],), ([0, 6, 12, 18, 25],)]),

    # Pair 11 (d = 0.65): recursion over arbitrarily nested lists.
    ("b11", "B", 0.65, "Nesting depth",
     "The value x is either an integer or a list whose elements are again integers or lists (nested to any depth). Return its nesting depth: an integer has depth 0, and a list has depth 1 plus the greatest depth among its elements. An empty list has depth 1.",
     "nest_depth(x)",
     "def nest_depth(x):\n    if not isinstance(x, list):\n        return 0\n    deepest = 0\n    for item in x:\n        deepest = max(deepest, nest_depth(item))\n    return 1 + deepest\n",
     [(5,), ([],), ([1, 2, 3],), ([1, [2]],), ([[[]]],), ([[1, 2], [3, [4, [5]]]],), ([[], [[]], 7],), ([[[[1]]], 2],)]),

    ("c11", "C", 0.65, "Sum of a nested list",
     "The value x is either an integer or a list whose elements are again integers or lists (nested to any depth). Return the sum of every integer found anywhere inside x. If x is itself an integer, return that integer. A list with no integers inside gives 0.",
     "nested_sum(x)",
     "def nested_sum(x):\n    if not isinstance(x, list):\n        return x\n    return sum(nested_sum(item) for item in x)\n",
     [(5,), ([],), ([1, 2, 3],), ([1, [2, [3]]],), ([[], [[]]],), ([[1, 2], [3, [4, [5]]]],), ([-4, [10, [-6]], 0],), ([[[[7]]], 3],)]),

    # Pair 12 (d = 1.0): sliding window over a sequence with a validity constraint.
    ("b12", "B", 1.0, "Longest two-letter stretch",
     "Given a string s, return the length of the longest contiguous substring that contains at most 2 distinct characters. The empty string gives 0.",
     "longest_two_distinct(s)",
     "def longest_two_distinct(s):\n    counts = {}\n    left = 0\n    best = 0\n    for right, ch in enumerate(s):\n        counts[ch] = counts.get(ch, 0) + 1\n        while len(counts) > 2:\n            counts[s[left]] -= 1\n            if counts[s[left]] == 0:\n                del counts[s[left]]\n            left += 1\n        best = max(best, right - left + 1)\n    return best\n",
     [("abcab",), ("",), ("aaaa",), ("eceba",), ("abaccc",), ("abcdef",), ("aabbccbbaa",), ("ab",)]),

    ("c12", "C", 1.0, "Longest light stretch",
     "Given a list nums of non-negative integers and a non-negative integer limit, return the length of the longest contiguous sub-list whose sum is at most limit. If no element fits (every single element exceeds limit) or nums is empty, return 0.",
     "longest_within_limit(nums, limit)",
     "def longest_within_limit(nums, limit):\n    left = 0\n    total = 0\n    best = 0\n    for right, v in enumerate(nums):\n        total += v\n        while total > limit and left <= right:\n            total -= nums[left]\n            left += 1\n        best = max(best, right - left + 1)\n    return best\n",
     [([1, 2, 3], 3), ([], 5), ([5, 6], 4), ([1, 1, 1, 1], 10), ([4, 1, 1, 1, 2, 3, 5], 5), ([0, 0, 7, 0], 0), ([2, 5, 1, 1, 1, 6], 4), ([3, 1, 2, 1, 1], 5)]),
]

"""Stub task bank. Difficulties are NOMINAL values on the filter's latent scale (about -2..+2).

A real pilot needs >= 150 items whose difficulties are calibrated from response data (IRT);
with a bank this small, tasks repeat and repeats must be excluded from analysis.
tests: list of [args, expected]; the function is called as fn(*args).
stakes: 0..1; tasks above 0.5 are "delivery-critical": always full help, never probed.
"""


def _t(id, title, d, fn, prompt, tests, hint, approach, solution, stakes=0.1):
    return dict(id=id, title=title, difficulty=d, fn=fn, prompt=prompt, tests=tests, stakes=stakes,
                starter=f"def {fn}({', '.join(_ARGS[fn])}):\n    # your code here\n    pass\n",
                hint=hint, approach=approach, solution=solution)


_ARGS = {"sum_list": ["nums"], "is_even": ["n"], "reverse_string": ["s"], "count_vowels": ["s"],
         "find_max": ["nums"], "fizzbuzz": ["n"], "is_palindrome": ["s"], "longest_common_prefix": ["strs"],
         "roman_to_int": ["s"], "word_frequency": ["text"], "flatten": ["nested"], "two_sum": ["nums", "target"],
         "group_anagrams": ["words"], "balanced_brackets": ["s"], "merge_intervals": ["intervals"]}

FB15 = ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"]

TASKS = [
    _t("sum_list", "Sum a list", -1.7, "sum_list", "Return the sum of the numbers in the list.",
       [[[[1, 2, 3]], 6], [[[]], 0], [[[-1, 1]], 0], [[[5]], 5], [[[10, 20, 30, 40]], 100]],
       "Start a running total at zero and add each number to it.",
       "Loop over the list keeping a total, then return it.",
       "def sum_list(nums):\n    total = 0\n    for x in nums:\n        total += x\n    return total\n"),
    _t("is_even", "Even or odd", -1.5, "is_even", "Return True if the integer n is even, else False.",
       [[[4], True], [[7], False], [[0], True], [[-3], False], [[-2], True]],
       "What does n % 2 give you for even numbers?", "Check the remainder when dividing by 2.",
       "def is_even(n):\n    return n % 2 == 0\n"),
    _t("reverse_string", "Reverse a string", -1.2, "reverse_string", "Return the string s reversed.",
       [[["abc"], "cba"], [[""], ""], [["a"], "a"], [["hello world"], "dlrow olleh"]],
       "Python slices accept a step; what does a step of -1 do?", "Slice the whole string with a negative step.",
       "def reverse_string(s):\n    return s[::-1]\n"),
    _t("count_vowels", "Count vowels", -1.0, "count_vowels",
       "Return how many vowels (a, e, i, o, u, either case) appear in s.",
       [[["hello"], 2], [[""], 0], [["xyz"], 0], [["AEIOU"], 5], [["Programming"], 3]],
       "Compare each lower-cased character against a string of vowels.",
       "Loop over the characters and count the ones that are in 'aeiou' after lower-casing.",
       "def count_vowels(s):\n    return sum(1 for ch in s.lower() if ch in 'aeiou')\n"),
    _t("find_max", "Largest number", -0.7, "find_max",
       "Return the largest number in a non-empty list without using max().",
       [[[[3, 1, 4]], 4], [[[-5, -2, -9]], -2], [[[7]], 7], [[[2, 2, 2]], 2]],
       "Keep the best value seen so far; start from the first element, not from 0.",
       "Initialise best to the first element, then update it whenever you see something larger.",
       "def find_max(nums):\n    best = nums[0]\n    for x in nums[1:]:\n        if x > best:\n            best = x\n    return best\n"),
    _t("fizzbuzz", "FizzBuzz", -0.5, "fizzbuzz",
       "Return a list of strings for 1..n: 'Fizz' for multiples of 3, 'Buzz' for 5, 'FizzBuzz' for both, else the number.",
       [[[5], ["1", "2", "Fizz", "4", "Buzz"]], [[15], FB15], [[0], []], [[3], ["1", "2", "Fizz"]]],
       "Test the multiple-of-15 case before the multiple-of-3 and multiple-of-5 cases.",
       "Loop 1..n; check divisibility by 15 first, then 3, then 5; otherwise use str(i).",
       "def fizzbuzz(n):\n    out = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            out.append('FizzBuzz')\n        elif i % 3 == 0:\n            out.append('Fizz')\n        elif i % 5 == 0:\n            out.append('Buzz')\n        else:\n            out.append(str(i))\n    return out\n"),
    _t("is_palindrome", "Palindrome check", -0.2, "is_palindrome",
       "Return True if s reads the same forwards and backwards, ignoring case and anything that is not a letter or digit.",
       [[["A man, a plan, a canal: Panama"], True], [["hello"], False], [[""], True],
        [["No 'x' in Nixon"], True], [["ab"], False]],
       "Clean the string first, then compare it with its reverse.",
       "Keep only alphanumeric characters, lower-case them, and compare with the reversed version.",
       "def is_palindrome(s):\n    t = [c.lower() for c in s if c.isalnum()]\n    return t == t[::-1]\n"),
    _t("word_frequency", "Word frequency", 0.1, "word_frequency",
       "Return a dict mapping each lower-cased word (split on whitespace) to how many times it appears.",
       [[["a b a"], {"a": 2, "b": 1}], [[""], {}], [["The the THE"], {"the": 3}]],
       "A dict's get(key, 0) saves you an if-statement.",
       "Lower-case the text, split it, and add one to a counter dict for every word.",
       "def word_frequency(text):\n    counts = {}\n    for w in text.lower().split():\n        counts[w] = counts.get(w, 0) + 1\n    return counts\n"),
    _t("longest_common_prefix", "Common prefix", 0.3, "longest_common_prefix",
       "Return the longest common prefix of a list of strings ('' if there is none or the list is empty).",
       [[[["flower", "flow", "flight"]], "fl"], [[["dog", "racecar", "car"]], ""], [[["a"]], "a"], [[[]], ""]],
       "Shrink a candidate prefix until every string starts with it.",
       "Take the first string as the prefix; for each other string, trim the prefix until the string starts with it.",
       "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = strs[0]\n    for s in strs[1:]:\n        while not s.startswith(prefix):\n            prefix = prefix[:-1]\n    return prefix\n"),
    _t("roman_to_int", "Roman numerals", 0.2, "roman_to_int", "Convert a Roman numeral string (I,V,X,L,C,D,M) to an integer.",
       [[["III"], 3], [["IV"], 4], [["IX"], 9], [["LVIII"], 58], [["MCMXCIV"], 1994]],
       "A smaller symbol before a larger one is subtracted.",
       "Map symbols to values; add each value, but subtract it when the next symbol is larger.",
       "def roman_to_int(s):\n    v = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n    total = 0\n    for i, ch in enumerate(s):\n        if i + 1 < len(s) and v[ch] < v[s[i + 1]]:\n            total -= v[ch]\n        else:\n            total += v[ch]\n    return total\n"),
    _t("flatten", "Flatten nested lists", 0.5, "flatten",
       "Flatten an arbitrarily nested list of integers into a single flat list, keeping order.",
       [[[[1, [2, [3, 4]], 5]], [1, 2, 3, 4, 5]], [[[]], []], [[[[[]]]], []], [[[1, 2, 3]], [1, 2, 3]],
        [[[[1], [2, [3]]]], [1, 2, 3]]],
       "When an element is itself a list, what function could handle it?",
       "Recurse: for each element, extend the result with flatten(element) if it is a list, else append it.",
       "def flatten(nested):\n    out = []\n    for x in nested:\n        if isinstance(x, list):\n            out.extend(flatten(x))\n        else:\n            out.append(x)\n    return out\n"),
    _t("two_sum", "Two sum", 0.7, "two_sum",
       "Return [i, j] with i < j such that nums[i] + nums[j] == target. Exactly one solution exists.",
       [[[[2, 7, 11, 15], 9], [0, 1]], [[[3, 2, 4], 6], [1, 2]], [[[3, 3], 6], [0, 1]], [[[1, 5, 3, 7], 10], [2, 3]]],
       "For each number, what other number would complete the target? Where could you look that up fast?",
       "Walk the list keeping a dict of value -> index; for each x, check whether target - x is already in the dict.",
       "def two_sum(nums, target):\n    seen = {}\n    for j, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], j]\n        seen[x] = j\n"),
    _t("group_anagrams", "Group anagrams", 0.9, "group_anagrams",
       "Group words that are anagrams of each other. Sort each group alphabetically, then sort the groups by their first word.",
       [[[["eat", "tea", "tan", "ate", "nat", "bat"]], [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]],
        [[[]], []], [[["a"]], [["a"]]], [[["ab", "ba", "abc"]], [["ab", "ba"], ["abc"]]]],
       "Anagrams share the same letters once sorted; use that as a dict key.",
       "Key each word by its sorted letters, collect words per key, then sort each group and the list of groups.",
       "def group_anagrams(words):\n    groups = {}\n    for w in words:\n        groups.setdefault(''.join(sorted(w)), []).append(w)\n    return sorted(sorted(g) for g in groups.values())\n"),
    _t("balanced_brackets", "Balanced brackets", 1.1, "balanced_brackets",
       "Return True if every (, [, { in s is closed in the right order, else False. Other characters are ignored.",
       [[["()[]{}"], True], [["(]"], False], [["([{}])"], True], [["((("], False], [[""], True], [["]"], False],
        [["{[]}"], True]],
       "Which data structure gives you the most recent unclosed bracket first?",
       "Push openers on a stack; on a closer, the stack top must be its matching opener. At the end the stack must be empty.",
       "def balanced_brackets(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in s:\n        if ch in '([{':\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n"),
    _t("merge_intervals", "Merge intervals (delivery task)", 1.4, "merge_intervals",
       "Merge all overlapping [start, end] intervals (touching counts as overlapping) and return them sorted by start.",
       [[[[[1, 3], [2, 6], [8, 10], [15, 18]]], [[1, 6], [8, 10], [15, 18]]], [[[[1, 4], [4, 5]]], [[1, 5]]],
        [[[]], []], [[[[5, 6], [1, 2]]], [[1, 2], [5, 6]]], [[[[1, 10], [2, 3]]], [[1, 10]]]],
       "Sorting by start makes overlaps adjacent.",
       "Sort by start; keep a result list; if the next interval starts at or before the last end, extend the last end, else append it.",
       "def merge_intervals(intervals):\n    out = []\n    for s, e in sorted(intervals):\n        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n        else:\n            out.append([s, e])\n    return out\n",
       stakes=0.9),
]

BY_ID = {t["id"]: t for t in TASKS}


def public_view(task):
    """What the browser may see: never tests, hints or the solution."""
    return {k: task[k] for k in ("id", "title", "prompt", "starter", "fn")}

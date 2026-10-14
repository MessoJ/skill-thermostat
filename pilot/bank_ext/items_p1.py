"""Practice items p21..p46: strings and text."""

ITEMS = [
    ("p21", "P", -1.3, "Count words",
     "s is a string. Return the number of words in s as an int, where a word is a maximal run of non-whitespace characters "
     "(words are separated by any whitespace). Return 0 if s has no words.",
     "count_words(s)",
     "def count_words(s):\n    return len(s.split())",
     [("hello world",), ("one",), ("",), ("  a  b   c ",), ("tab\tseparated\nlines here",), ("   ",)]),

    ("p22", "P", -1.2, "Swap case",
     "s is an ASCII string. Return a new string in which every uppercase letter is lowercase and every lowercase letter is "
     "uppercase. All other characters are unchanged.",
     "swap_case(s)",
     "def swap_case(s):\n    return ''.join(c.lower() if c.isupper() else c.upper() for c in s)",
     [("Hello World",), ("abc",), ("",), ("ABC",), ("a1B2 c!",), ("MiXeD",)]),

    ("p23", "P", -1.0, "Digits only",
     "s is a string. Return a string made of just the digit characters ('0' to '9') of s, in their original order. "
     "Return the empty string if s has no digits.",
     "digits_only(s)",
     "def digits_only(s):\n    return ''.join(c for c in s if c in '0123456789')",
     [("a1b2c3",), ("abc",), ("",), ("2024-01-15",), ("007 bond",), ("9",)]),

    ("p24", "P", -0.9, "Repeat each character",
     "s is a string and n is an int with n >= 0. Return a string in which every character of s is repeated n times in place "
     "(for example 'ab' with n=2 gives 'aabb'). If n is 0 or s is empty, return the empty string.",
     "repeat_chars(s, n)",
     "def repeat_chars(s, n):\n    return ''.join(c * n for c in s)",
     [("abc", 2), ("xy", 1), ("", 3), ("ab", 0), ("a b", 3), ("Hi!", 4)]),

    ("p25", "P", -0.7, "Initials",
     "s is a string of words separated by whitespace. Return a string made of the first character of each word, converted to "
     "uppercase, in order. Return the empty string if s has no words.",
     "initials(s)",
     "def initials(s):\n    return ''.join(w[0].upper() for w in s.split())",
     [("portable network graphics",), ("hello",), ("",), ("  as soon   as possible ",), ("mIxEd cAsE",), ("a b c d e",)]),

    ("p26", "P", -0.6, "Longest word",
     "s is a string. Words are the maximal runs of non-whitespace characters (punctuation counts as part of a word). Return the "
     "longest word in s. If several words tie for longest, return the earliest one. Return the empty string if s has no words.",
     "longest_word(s)",
     "def longest_word(s):\n    best = ''\n    for w in s.split():\n        if len(w) > len(best):\n            best = w\n    return best",
     [("the quick brown fox",), ("a",), ("",), ("cat dog bird",), ("one three, five seven",), ("hi   there you!",), ("aa bb cc",)]),

    ("p27", "P", -0.5, "Vowel-initial words",
     "s is a string of words separated by whitespace. Return a list of the words whose first character is a vowel "
     "(a, e, i, o, u, in either case), in their original order and original case. Return [] if there are none.",
     "vowel_words(s)",
     "def vowel_words(s):\n    return [w for w in s.split() if w[0].lower() in 'aeiou']",
     [("an apple a day",), ("rhythm myth",), ("",), ("Eat Ice cream Under Oak",), ("umbrella",), ("  orange   banana  ",)]),

    ("p28", "P", -0.4, "Alternating case",
     "s is an ASCII string. Return a new string in which the character at every even index (0, 2, 4, ...) is converted to "
     "lowercase and the character at every odd index is converted to uppercase. Indices count every character, including "
     "spaces and punctuation, which are left as they are.",
     "alternating_case(s)",
     "def alternating_case(s):\n    return ''.join(c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(s))",
     [("hello",), ("a",), ("",), ("Hello World",), ("ABCDEF",), ("x-y z",)]),

    ("p29", "P", -0.2, "Caesar cipher",
     "s is a string and k is an int with k >= 0. Shift every English letter forward by k positions in the alphabet, wrapping "
     "from z back to a, and keep its case ('a'-'z' stay lowercase, 'A'-'Z' stay uppercase). Characters that are not ASCII "
     "letters are unchanged. k may be larger than 26.",
     "caesar(s, k)",
     "def caesar(s, k):\n    out = []\n    for c in s:\n        if 'a' <= c <= 'z':\n"
     "            out.append(chr((ord(c) - 97 + k) % 26 + 97))\n        elif 'A' <= c <= 'Z':\n"
     "            out.append(chr((ord(c) - 65 + k) % 26 + 65))\n        else:\n            out.append(c)\n    return ''.join(out)",
     [("abc", 1), ("xyz", 3), ("Hello, World!", 13), ("abc", 0), ("abc", 26), ("Zebra", 30), ("", 5), ("Az-9", 53)]),

    ("p30", "P", 0.0, "Anagram check",
     "a and b are strings. Return True if a and b contain exactly the same letters with the same counts, after ignoring case "
     "and ignoring every character that is not an English letter (spaces, digits and punctuation are ignored). Otherwise return "
     "False. Two strings with no letters are anagrams of each other.",
     "are_anagrams(a, b)",
     "def are_anagrams(a, b):\n    f = lambda t: sorted(c.lower() for c in t if c.isalpha())\n    return f(a) == f(b)",
     [("listen", "silent"), ("abc", "abd"), ("Dormitory", "dirty room"), ("", ""), ("aab", "abb"), ("a", "aa"),
      ("Hello, World", "Wordl Hello!"), ("a1", "a2"), ("ab", "abc")]),

    ("p31", "P", 0.1, "Overlapping count",
     "s and sub are strings and sub is non-empty. Return the number of indices i such that s starts with sub at position i. "
     "Occurrences may overlap (for example 'aaaa' contains 'aa' 3 times). Return 0 if sub does not occur.",
     "count_overlapping(s, sub)",
     "def count_overlapping(s, sub):\n    return sum(1 for i in range(len(s) - len(sub) + 1) if s[i:i + len(sub)] == sub)",
     [("banana", "an"), ("aaaa", "aa"), ("abc", "d"), ("", "a"), ("abababa", "aba"), ("aaa", "aaaa"), ("hello", "l"),
      ("aaaaa", "a")]),

    ("p32", "P", 0.2, "Camel to snake",
     "s is a string of ASCII letters and digits in camelCase or PascalCase. Return it in snake_case: insert an underscore "
     "immediately before every uppercase letter that is not the first character of s, then convert the whole string to "
     "lowercase. Every uppercase letter is treated separately, so 'getHTTP' becomes 'get_h_t_t_p'. Return '' for ''.",
     "camel_to_snake(s)",
     "def camel_to_snake(s):\n    out = []\n    for i, c in enumerate(s):\n        if c.isupper() and i > 0:\n"
     "            out.append('_')\n        out.append(c.lower())\n    return ''.join(out)",
     [("camelCase",), ("word",), ("PascalCase",), ("",), ("getHTTPResponse",), ("a1B",), ("X",), ("aB",)]),

    ("p33", "P", 0.3, "First unique character",
     "s is a string. Return the first character of s (scanning left to right) that appears exactly once in s. Comparison is "
     "case-sensitive. Return the empty string if no character appears exactly once.",
     "first_unique(s)",
     "def first_unique(s):\n    for c in s:\n        if s.count(c) == 1:\n            return c\n    return ''",
     [("swiss",), ("abc",), ("aabb",), ("",), ("aabcc",), ("Aa",), ("loveleetcode",), ("abab",)]),

    ("p34", "P", 0.4, "Run-length decode",
     "s is a run-length encoded string: a concatenation of groups, each being a positive integer count (one or more digits, "
     "no leading zeros) followed by a single lowercase letter, for example '3a2b1c'. Return the decoded string ('aaabbc' for "
     "that example). Counts can have several digits. Return '' if s is ''. The same letter may appear in consecutive groups.",
     "rle_decode(s)",
     "def rle_decode(s):\n    out = []\n    num = ''\n    for c in s:\n        if c.isdigit():\n            num += c\n"
     "        else:\n            out.append(c * int(num))\n            num = ''\n    return ''.join(out)",
     [("3a2b1c",), ("1a",), ("",), ("12x",), ("2a3a",), ("10a1b",), ("1z1y1x",)]),

    ("p35", "P", 0.5, "Thousands separators",
     "n is an int (possibly negative or zero). Return its decimal representation as a string with a comma between every group "
     "of three digits, counting from the right (for example 1234567 gives '1,234,567'). A negative number keeps a leading '-' "
     "before the first digit group (for example -1234 gives '-1,234').",
     "add_commas(n)",
     "def add_commas(n):\n    s = str(abs(n))\n    parts = []\n    while len(s) > 3:\n        parts.append(s[-3:])\n"
     "        s = s[:-3]\n    parts.append(s)\n    return ('-' if n < 0 else '') + ','.join(reversed(parts))",
     [(1234567,), (999,), (0,), (1000,), (-1234,), (-999,), (100000,), (12345678901,), (-1000000,)]),

    ("p36", "P", 0.6, "Pig Latin",
     "s is a string of lowercase English words separated by single spaces (s may be empty). Convert each word: if it starts "
     "with a vowel (a, e, i, o, u) append 'way'; otherwise move all the leading consonants (every letter before the first "
     "vowel) to the end of the word and append 'ay'. The letter 'y' counts as a consonant. A word with no vowel is moved "
     "entirely, so 'rhythm' becomes 'rhythmay'. Return the converted words joined by single spaces ('' for '').",
     "pig_latin(s)",
     "def pig_latin(s):\n    out = []\n    for w in s.split(' ') if s else []:\n        if w[0] in 'aeiou':\n"
     "            out.append(w + 'way')\n        else:\n            i = 0\n            while i < len(w) and w[i] not in 'aeiou':\n"
     "                i += 1\n            out.append(w[i:] + w[:i] + 'ay')\n    return ' '.join(out)",
     [("hello",), ("apple",), ("string theory",), ("",), ("rhythm",), ("i am",), ("yellow",), ("the quick brown fox",)]),

    ("p37", "P", 0.65, "Parse key=value pairs",
     "s is a string of segments separated by ';'. For every segment: strip leading and trailing whitespace; ignore it if it is "
     "empty or contains no '='; otherwise split it at the FIRST '=' into a key and a value and strip whitespace around each. "
     "Return a dict mapping each key to its value (both strings, the value may be empty). If a key appears more than once the "
     "last value wins. Return {} if there are no valid segments.",
     "parse_pairs(s)",
     "def parse_pairs(s):\n    out = {}\n    for seg in s.split(';'):\n        seg = seg.strip()\n        if '=' not in seg:\n"
     "            continue\n        k, v = seg.split('=', 1)\n        out[k.strip()] = v.strip()\n    return out",
     [("a=1;b=2",), ("",), (" x = hello world ; y=2 ;",), ("k=1;k=2",), ("a=b=c",), ("novalue;a=1",), ("a=;b=2",), (";;  ;",)]),

    ("p38", "P", 0.75, "Compare versions",
     "a and b are version strings made of non-negative integers separated by '.', such as '1.2.10' (no empty parts). Compare "
     "them part by part as numbers (so 10 is greater than 2), treating a missing part as 0 (so '1.0' equals '1' and '1.0.1' "
     "is greater than '1'). Return -1 if a is lower than b, 1 if a is greater than b, and 0 if they are equal.",
     "compare_versions(a, b)",
     "def compare_versions(a, b):\n    x = [int(p) for p in a.split('.')]\n    y = [int(p) for p in b.split('.')]\n"
     "    n = max(len(x), len(y))\n    x += [0] * (n - len(x))\n    y += [0] * (n - len(y))\n"
     "    return (x > y) - (x < y)",
     [("1.2", "1.10"), ("1.0", "1"), ("2.0.1", "2"), ("1.2.3", "1.2.3"), ("0.9", "1.0"), ("1.0.0.0", "1"),
      ("10.0", "9.9.9"), ("1", "1.0.1"), ("3.4.5", "3.4.10")]),

    ("p39", "P", 0.8, "Word wrap",
     "s is a string and w is an int with w >= 1. Split s into words on whitespace and lay them out greedily into lines: put "
     "each word on the current line, separated by a single space, if the line would then be at most w characters long; "
     "otherwise start a new line with that word. Every word is guaranteed to have length at most w. Return the list of lines "
     "(each with no leading or trailing spaces). Return [] if s has no words.",
     "wrap_text(s, w)",
     "def wrap_text(s, w):\n    lines = []\n    cur = ''\n    for word in s.split():\n        if not cur:\n            cur = word\n"
     "        elif len(cur) + 1 + len(word) <= w:\n            cur += ' ' + word\n        else:\n            lines.append(cur)\n"
     "            cur = word\n    if cur:\n        lines.append(cur)\n    return lines",
     [("the quick brown fox", 10), ("hello", 5), ("", 5), ("a b c", 1), ("aaa bb c dd eeee", 6), ("a b c d e f", 3),
      ("one two three four five six", 20), ("  spaced    out  words  ", 8)]),

    ("p40", "P", 0.9, "Longest distinct run",
     "s is a string. Return the length of the longest contiguous substring of s in which no character appears twice "
     "(case-sensitive). Return 0 for the empty string.",
     "longest_distinct(s)",
     "def longest_distinct(s):\n    last = {}\n    start = 0\n    best = 0\n    for i, c in enumerate(s):\n"
     "        if c in last and last[c] >= start:\n            start = last[c] + 1\n        last[c] = i\n"
     "        best = max(best, i - start + 1)\n    return best",
     [("abcabcbb",), ("bbbb",), ("",), ("pwwkew",), ("abcdef",), ("abba",), ("dvdf",), ("tmmzuxt",), ("aAbB",)]),

    ("p41", "P", 1.0, "Longest palindromic substring",
     "s is a string. Return the longest contiguous substring of s that reads the same forwards and backwards (case-sensitive, "
     "every character counts). If several have the same maximum length, return the one that starts earliest. Return '' for "
     "the empty string. A single character is a palindrome.",
     "longest_palindrome(s)",
     "def longest_palindrome(s):\n    best = ''\n    n = len(s)\n    for c in range(2 * n - 1):\n        l, r = c // 2, c // 2 + c % 2\n"
     "        while l >= 0 and r < n and s[l] == s[r]:\n            l -= 1\n            r += 1\n"
     "        if r - l - 1 > len(best):\n            best = s[l + 1:r]\n    return best",
     [("babad",), ("cbbd",), ("a",), ("",), ("abc",), ("forgeeksskeegfor",), ("abacdfgdcaba",), ("racecar",), ("aaaa",),
      ("xabbay",)]),

    ("p42", "P", 1.05, "Spreadsheet column title",
     "n is an int with n >= 1. Return the spreadsheet column label for column number n, where 1 is 'A', 2 is 'B', ..., 26 is "
     "'Z', 27 is 'AA', 28 is 'AB', ..., 52 is 'AZ', 53 is 'BA', ..., 702 is 'ZZ', 703 is 'AAA', and so on.",
     "column_title(n)",
     "def column_title(n):\n    out = []\n    while n > 0:\n        n, r = divmod(n - 1, 26)\n        out.append(chr(65 + r))\n"
     "    return ''.join(reversed(out))",
     [(1,), (26,), (27,), (28,), (52,), (53,), (701,), (702,), (703,), (18278,)]),

    ("p43", "P", 1.1, "Simplify path",
     "p is an absolute Unix-style path string that starts with '/'. Components are separated by one or more '/'. A component "
     "'.' means the current directory and is ignored; '..' means go up one directory (at the root it does nothing); any other "
     "component (including ones like '...' or 'a.b') is an ordinary name. Return the canonical path: it starts with a single "
     "'/', names are separated by single '/', and there is no trailing '/' (the root is just '/').",
     "simplify_path(p)",
     "def simplify_path(p):\n    stack = []\n    for part in p.split('/'):\n        if part == '' or part == '.':\n            continue\n"
     "        if part == '..':\n            if stack:\n                stack.pop()\n        else:\n            stack.append(part)\n"
     "    return '/' + '/'.join(stack)",
     [("/home/",), ("/a/b",), ("/../",), ("/a/./b/../../c/",), ("/a//b////c/d//././/..",), ("/",), ("/.../a",),
      ("/a/b/c/../../../..",), ("/a/b/../c",)]),

    ("p44", "P", 1.2, "Edit distance",
     "a and b are strings. Return the minimum number of single-character operations needed to turn a into b, where an "
     "operation is inserting a character, deleting a character, or replacing one character with another (Levenshtein "
     "distance). Comparison is case-sensitive.",
     "edit_distance(a, b)",
     "def edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a, 1):\n        cur = [i]\n"
     "        for j, cb in enumerate(b, 1):\n            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))\n"
     "        prev = cur\n    return prev[-1]",
     [("kitten", "sitting"), ("abc", "abc"), ("", "abc"), ("", ""), ("flaw", "lawn"), ("intention", "execution"),
      ("a", "b"), ("sunday", "saturday"), ("abc", ""), ("ab", "ba")]),

    ("p45", "P", 1.3, "Decode nested repeats",
     "s encodes a string using the pattern k[text], meaning text repeated k times, where k is a positive integer (one or more "
     "digits) and text may itself contain other k[...] patterns, nested to any depth. Letters outside any bracket are copied "
     "as they are. s is guaranteed well formed, and digits only appear as repeat counts. Return the fully decoded string. "
     "For example '3[a2[c]]' decodes to 'accaccacc'.",
     "decode_string(s)",
     "def decode_string(s):\n    stack = []\n    cur = ''\n    num = 0\n    for c in s:\n        if c.isdigit():\n"
     "            num = num * 10 + int(c)\n        elif c == '[':\n            stack.append((cur, num))\n            cur, num = '', 0\n"
     "        elif c == ']':\n            prev, k = stack.pop()\n            cur = prev + cur * k\n        else:\n            cur += c\n"
     "    return cur",
     [("3[a]2[bc]",), ("abc",), ("",), ("3[a2[c]]",), ("2[abc]3[cd]ef",), ("10[a]",), ("2[2[2[x]]]",), ("a2[b]c",),
      ("2[a2[b]c]",)]),

    ("p46", "P", 1.4, "Minimum window substring",
     "s and t are strings and t is non-empty. Return the shortest contiguous substring of s that contains every character of t "
     "at least as many times as it appears in t (so t='aab' needs two 'a' and one 'b'). Comparison is case-sensitive. If "
     "several shortest windows exist, return the one that starts earliest. Return '' if no such substring exists.",
     "min_window(s, t)",
     "def min_window(s, t):\n    from collections import Counter\n    need = Counter(t)\n    missing = len(t)\n    best = ''\n"
     "    left = 0\n    for right, c in enumerate(s):\n        if need[c] > 0:\n            missing -= 1\n        need[c] -= 1\n"
     "        if missing == 0:\n            while need[s[left]] < 0:\n                need[s[left]] += 1\n                left += 1\n"
     "            if not best or right - left + 1 < len(best):\n                best = s[left:right + 1]\n"
     "            need[s[left]] += 1\n            missing += 1\n            left += 1\n    return best",
     [("ADOBECODEBANC", "ABC"), ("a", "a"), ("a", "aa"), ("abc", "b"), ("aa", "aa"), ("xyz", "a"), ("abcab", "ab"),
      ("cabwefgewcwaefgcf", "cae"), ("aaflslflsldkalskaaa", "aaa"), ("ab", "ba")]),
]

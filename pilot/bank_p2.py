"""Practice-pool items p59..p96 (d from 0.0 to 1.6)."""

ITEMS = [
    dict(
        id="p59", pool="P", d=0.0, title="Totals by name",
        prompt="Given a list of [name, amount] pairs, return a dict mapping each name to the sum of its amounts. An empty list gives an empty dict.",
        sig="total_by_key(pairs)",
        ref='''
def total_by_key(pairs):
    out = {}
    for name, amount in pairs:
        out[name] = out.get(name, 0) + amount
    return out
''',
        cases=[
            ([["a", 1], ["b", 2], ["a", 3]],),
            ([["x", 5], ["y", -2]],),
            ([],),
            ([["solo", 7]],),
            ([["a", 1], ["a", -1]],),
            ([["A", 1], ["a", 2], ["A", 3]],),
            ([["k", 0], ["m", 4], ["k", 0], ["m", 6]],),
            ([["n%d" % (i % 5), i] for i in range(100)],),
        ],
    ),
    dict(
        id="p60", pool="P", d=0.0, title="Caesar shift",
        prompt="Shift every letter forward by k places in the alphabet, wrapping around from z to a, and keep its case. Characters that are not letters stay unchanged. k may be negative or larger than 26.",
        sig="caesar_shift(text, k)",
        ref='''
def caesar_shift(text, k):
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + k) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)
''',
        cases=[
            ("abc", 1),
            ("Hello, World!", 3),
            ("xyz", 3),
            ("", 5),
            ("Zebra", -1),
            ("abc", 52),
            ("Python 3.11", -27),
            ("aZ", 25),
            ("The quick brown fox", 13),
        ],
    ),
    dict(
        id="p61", pool="P", d=0.1, title="Acronym builder",
        prompt="Return the first letter of each whitespace-separated word, in uppercase, joined into one string. Words may be separated by several spaces; an empty or all-space phrase gives an empty string.",
        sig="acronym(phrase)",
        ref='''
def acronym(phrase):
    return "".join(w[0].upper() for w in phrase.split())
''',
        cases=[
            ("portable network graphics",),
            ("as soon as possible",),
            ("",),
            ("  hello   big world ",),
            ("single",),
            ("123 go",),
            ("   ",),
            ("Read Only Memory",),
        ],
    ),
    dict(
        id="p62", pool="P", d=0.1, title="Longest run",
        prompt="Return the length of the longest block of equal values that sit next to each other in the list. An empty list gives 0.",
        sig="longest_run(xs)",
        ref='''
def longest_run(xs):
    best = 0
    cur = 0
    prev = None
    for i, x in enumerate(xs):
        if i > 0 and x == prev:
            cur += 1
        else:
            cur = 1
        prev = x
        best = max(best, cur)
    return best
''',
        cases=[
            ([1, 1, 2, 2, 2, 3],),
            (["a", "b", "b"],),
            ([],),
            ([7],),
            ([1, 2, 3],),
            ([4, 4, 4, 4],),
            ([1, 1, 2, 1, 1, 1],),
            ([0, 0, -1, -1],),
            ([None, None, 0],),
        ],
    ),
    dict(
        id="p63", pool="P", d=0.2, title="Diagonal sum",
        prompt="Given a square matrix (list of equal-length rows), return the sum of the main diagonal plus the anti-diagonal, counting the centre element only once when the size is odd. An empty matrix gives 0.",
        sig="diagonal_sum(matrix)",
        ref='''
def diagonal_sum(matrix):
    n = len(matrix)
    total = 0
    for i in range(n):
        total += matrix[i][i]
        if i != n - 1 - i:
            total += matrix[i][n - 1 - i]
    return total
''',
        cases=[
            ([[1, 2], [3, 4]],),
            ([[1, 2, 3], [4, 5, 6], [7, 8, 9]],),
            ([],),
            ([[5]],),
            ([[1, -1, 1, -1], [2, 2, 2, 2], [3, 3, 3, 3], [-4, 4, 4, -4]],),
            ([[0, 0], [0, 9]],),
            ([[i * 5 + j for j in range(5)] for i in range(5)],),
        ],
    ),
    dict(
        id="p64", pool="P", d=0.2, title="First unique character",
        prompt="Return the first character of s that appears exactly once in s (case-sensitive, so 'A' and 'a' differ). If there is no such character, return an empty string.",
        sig="first_unique(s)",
        ref='''
def first_unique(s):
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in s:
        if counts[ch] == 1:
            return ch
    return ""
''',
        cases=[
            ("swiss",),
            ("aabbc",),
            ("aabb",),
            ("",),
            ("a",),
            ("Aa",),
            ("abcabcd",),
            ("loveleetcode",),
        ],
    ),
    dict(
        id="p65", pool="P", d=0.3, title="Heaviest row",
        prompt="Given a list of rows of numbers, return the index of the row with the largest sum; on a tie return the smallest index. Rows may be empty (sum 0). An empty grid gives -1.",
        sig="row_with_max_sum(grid)",
        ref='''
def row_with_max_sum(grid):
    best = -1
    best_sum = None
    for i, row in enumerate(grid):
        s = sum(row)
        if best_sum is None or s > best_sum:
            best, best_sum = i, s
    return best
''',
        cases=[
            ([[1, 2], [5, 5], [0, 3]],),
            ([[2, 2], [1, 3]],),
            ([],),
            ([[]],),
            ([[-1], [-2]],),
            ([[], [1]],),
            ([[0], [], [-3]],),
            ([[1], [4], [2, 2]],),
            ([[7, 7], [2], [3, 3]],),
            ([[3, 3], [2, 2, 2], [6]],),
            ([[-5, -5], [-1], [-9, 4]],),
        ],
    ),
    dict(
        id="p66", pool="P", d=0.3, title="Merge two lists",
        prompt="Given two lists each already in ascending order, return one ascending list containing all elements of both, keeping duplicates. Either list may be empty.",
        sig="merge_sorted(a, b)",
        ref='''
def merge_sorted(a, b):
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out
''',
        cases=[
            ([1, 3, 5], [2, 4, 6]),
            ([1, 2], [2, 3]),
            ([], []),
            ([], [1, 2]),
            ([5], []),
            ([-3, -1, 4], [-2, -2, 10]),
            (list(range(0, 2000, 2)), list(range(1, 2000, 2))),
            ([1, 1, 1], [1, 1]),
        ],
    ),
    dict(
        id="p67", pool="P", d=0.3, title="Rank students",
        prompt="Given [name, score] records, return the names ordered by score from highest to lowest; students with equal scores are ordered by name using plain string comparison (so 'B' comes before 'a'). An empty list gives [].",
        sig="rank_students(records)",
        ref='''
def rank_students(records):
    return [name for name, score in sorted(records, key=lambda r: (-r[1], r[0]))]
''',
        cases=[
            ([["bo", 70], ["al", 90], ["cy", 80]],),
            ([["bo", 80], ["al", 80], ["cy", 90]],),
            ([],),
            ([["z", 1]],),
            ([["B", 5], ["a", 5], ["C", 5]],),
            ([["x", -1], ["y", -5], ["w", -1]],),
            ([["m%d" % i, i % 4] for i in range(12)],),
        ],
    ),
    dict(
        id="p68", pool="P", d=0.4, title="GCD of list",
        prompt="Return the greatest common divisor of all integers in the list, as a non-negative number (ignore signs). An empty list or a list of only zeros gives 0.",
        sig="gcd_list(xs)",
        ref='''
def gcd_list(xs):
    g = 0
    for x in xs:
        a, b = g, abs(x)
        while b:
            a, b = b, a % b
        g = a
    return g
''',
        cases=[
            ([12, 18, 24],),
            ([7, 13],),
            ([],),
            ([0, 0],),
            ([-8, 12],),
            ([0, 5],),
            ([100],),
            ([42, 0, -14],),
            ([270, 360, 450, 90],),
        ],
    ),
    dict(
        id="p69", pool="P", d=0.4, title="Parse settings",
        prompt="Parse text such as 'a=1; b=-2' into a dict of string keys to int values. Pairs are separated by ';', key and value by '=', and spaces around either are ignored. Empty pairs are skipped and a repeated key keeps its last value.",
        sig="parse_kv(text)",
        ref='''
def parse_kv(text):
    out = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, value = part.split("=")
        out[key.strip()] = int(value.strip())
    return out
''',
        cases=[
            ("a=1;b=2",),
            ("x = 10 ; y=-3",),
            ("",),
            (";;",),
            ("k=1;k=2;j=3",),
            (" a=5;",),
            ("name=007",),
            ("a=1;;b=2;",),
        ],
    ),
    dict(
        id="p70", pool="P", d=0.5, title="Primes up to",
        prompt="Return the list of all prime numbers less than or equal to n, in ascending order. If n is less than 2 return an empty list.",
        sig="primes_up_to(n)",
        ref='''
def primes_up_to(n):
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = False
    return [i for i in range(n + 1) if sieve[i]]
''',
        cases=[
            (10,),
            (20,),
            (1,),
            (2,),
            (0,),
            (-5,),
            (97,),
            (30000,),
            (3,),
        ],
    ),
    dict(
        id="p71", pool="P", d=0.5, title="Prime factors",
        prompt="Return the prime factors of n in ascending order, repeating a prime as many times as it divides n (12 gives [2, 2, 3]). If n is less than 2 return an empty list.",
        sig="prime_factors(n)",
        ref='''
def prime_factors(n):
    out = []
    if n < 2:
        return out
    p = 2
    while p * p <= n:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1:
        out.append(n)
    return out
''',
        cases=[
            (12,),
            (30,),
            (1,),
            (2,),
            (97,),
            (0,),
            (360,),
            (1000003,),
            (2 ** 20,),
            (-12,),
        ],
    ),
    dict(
        id="p72", pool="P", d=0.6, title="First occurrence index",
        prompt="Given a list in ascending order (duplicates possible) and a target, return the smallest index at which target appears, or -1 if it does not appear.",
        sig="leftmost_index(xs, target)",
        ref='''
def leftmost_index(xs, target):
    lo, hi = 0, len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if lo < len(xs) and xs[lo] == target:
        return lo
    return -1
''',
        cases=[
            ([1, 2, 2, 3], 2),
            ([1, 3, 5], 4),
            ([], 1),
            ([2], 2),
            ([2, 2, 2, 2], 2),
            ([1, 2, 3, 4, 5], 5),
            ([-5, -3, -3, 0], -3),
            ([1] * 50000 + [2] * 50000, 2),
            ([1, 2, 3], 0),
        ],
    ),
    dict(
        id="p73", pool="P", d=0.6, title="Bits up to n",
        prompt="Return the total number of 1 bits in the binary representations of every integer from 0 to n inclusive (for n = 5: 0,1,1,2,1,2 sums to 7). If n is negative, return 0.",
        sig="bits_upto(n)",
        ref='''
def bits_upto(n):
    total = 0
    for i in range(n + 1):
        total += bin(i).count("1")
    return total
''',
        cases=[
            (5,),
            (8,),
            (0,),
            (1,),
            (-3,),
            (1000,),
            (100000,),
            (255,),
        ],
    ),
    dict(
        id="p74", pool="P", d=0.6, title="Postfix calculator",
        prompt="Evaluate a postfix (reverse Polish) expression given as a list of string tokens: integers (possibly negative, like '-3') and the operators + - * /. Division is integer division truncating toward zero. The input is always valid and non-empty.",
        sig="eval_rpn(tokens)",
        ref='''
def eval_rpn(tokens):
    stack = []
    for t in tokens:
        if t in ("+", "-", "*", "/"):
            b = stack.pop()
            a = stack.pop()
            if t == "+":
                stack.append(a + b)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(a * b)
            else:
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                stack.append(q)
        else:
            stack.append(int(t))
    return stack[0]
''',
        cases=[
            (["2", "3", "+"],),
            (["4", "13", "5", "/", "+"],),
            (["5"],),
            (["-7", "2", "/"],),
            (["7", "-2", "/"],),
            (["3", "4", "-", "2", "*"],),
            (["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"],),
            (["-8", "-3", "/"],),
        ],
    ),
    dict(
        id="p75", pool="P", d=0.7, title="Longest distinct substring",
        prompt="Return the length of the longest contiguous substring of s in which no character repeats (case-sensitive, so 'A' and 'a' are different). An empty string gives 0.",
        sig="longest_unique_run(s)",
        ref='''
def longest_unique_run(s):
    last = {}
    start = 0
    best = 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best
''',
        cases=[
            ("abcabcbb",),
            ("bbbb",),
            ("",),
            ("pwwkew",),
            ("abcdef",),
            ("aAbB",),
            ("dvdf",),
            ("abba",),
            ("ab" * 5000 + "c",),
        ],
    ),
    dict(
        id="p76", pool="P", d=0.7, title="Breadth-first levels",
        prompt="graph is a dict from node name to a list of neighbour names (directed, as given). Return a list of levels: the nodes first reachable in 0, 1, 2, ... steps from start, each level sorted alphabetically. Nodes missing from graph have no neighbours; start is always level 0.",
        sig="bfs_levels(graph, start)",
        ref='''
def bfs_levels(graph, start):
    seen = {start}
    level = [start]
    out = []
    while level:
        out.append(sorted(level))
        nxt = []
        for node in level:
            for nb in graph.get(node, []):
                if nb not in seen:
                    seen.add(nb)
                    nxt.append(nb)
        level = nxt
    return out
''',
        cases=[
            ({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}, "a"),
            ({"a": ["b"], "b": ["a"]}, "a"),
            ({}, "x"),
            ({"a": []}, "a"),
            ({"a": ["b"], "b": ["c"], "c": ["a"], "z": ["a"]}, "a"),
            ({"s": ["t", "r"], "r": ["u"], "t": ["u", "s"]}, "s"),
            ({"a": ["a", "b", "b"], "b": ["c"], "c": ["d", "a"], "d": ["e"]}, "b"),
        ],
    ),
    dict(
        id="p77", pool="P", d=0.8, title="Count islands",
        prompt="grid is a list of equal-length strings of '0' and '1'. Count the groups of '1' cells connected up, down, left or right (diagonals do not connect). An empty grid gives 0.",
        sig="count_islands(grid)",
        ref='''
def count_islands(grid):
    rows = len(grid)
    seen = set()
    count = 0
    for r in range(rows):
        for c in range(len(grid[r])):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                seen.add((r, c))
                stack = [(r, c)]
                while stack:
                    y, x = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < len(grid[ny]) and grid[ny][nx] == "1" and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
    return count
''',
        cases=[
            (["110", "010", "001"],),
            (["101", "010", "101"],),
            ([],),
            (["0"],),
            (["1"],),
            (["1111"],),
            (["10", "01"],),
            ([("10" * 15) if r % 2 == 0 else ("01" * 15) for r in range(30)],),
            (["11011", "11011", "00100", "00011"],),
        ],
    ),
    dict(
        id="p78", pool="P", d=0.8, title="Subarrays with sum",
        prompt="Count the contiguous, non-empty subarrays of xs whose elements add up to k. The list may contain negatives and zeros; different positions count separately even if the values match.",
        sig="subarrays_with_sum(xs, k)",
        ref='''
def subarrays_with_sum(xs, k):
    seen = {0: 1}
    total = 0
    count = 0
    for x in xs:
        total += x
        count += seen.get(total - k, 0)
        seen[total] = seen.get(total, 0) + 1
    return count
''',
        cases=[
            ([1, 1, 1], 2),
            ([1, 2, 3], 3),
            ([], 0),
            ([0, 0, 0], 0),
            ([1, -1, 1, -1], 0),
            ([5], 5),
            ([3, 4, 7, 2, -3, 1, 4, 2], 7),
            ([1, -1] * 1500, 0),
            ([2, 2, 2], 7),
        ],
    ),
    dict(
        id="p79", pool="P", d=0.9, title="Fewest coins",
        prompt="Given positive coin values (each usable any number of times) and a target amount, return the smallest number of coins that add up to exactly amount. Amount 0 needs 0 coins; return -1 if the amount cannot be made.",
        sig="min_coins(coins, amount)",
        ref='''
def min_coins(coins, amount):
    INF = float("inf")
    best = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and best[a - c] + 1 < best[a]:
                best[a] = best[a - c] + 1
    return best[amount] if best[amount] != INF else -1
''',
        cases=[
            ([1, 2, 5], 11),
            ([2], 3),
            ([1], 0),
            ([], 5),
            ([186, 419, 83, 408], 6249),
            ([3, 7], 11),
            ([5, 10, 25], 30),
            ([1, 3, 4], 6),
            ([7], 7),
        ],
    ),
    dict(
        id="p80", pool="P", d=0.9, title="Shortest grid path",
        prompt="grid is a list of equal-length strings of '.' (open) and '#' (wall). Return the fewest up/down/left/right moves from the top-left cell to the bottom-right cell through open cells, or -1 if impossible (including when either corner is a wall or the grid is empty).",
        sig="grid_steps(grid)",
        ref='''
def grid_steps(grid):
    if not grid or not grid[0]:
        return -1
    rows, cols = len(grid), len(grid[0])
    if grid[0][0] == "#" or grid[rows - 1][cols - 1] == "#":
        return -1
    dist = {(0, 0): 0}
    queue = [(0, 0)]
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        if (r, c) == (rows - 1, cols - 1):
            return dist[(r, c)]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                queue.append((nr, nc))
    return -1
''',
        cases=[
            (["..", "#."],),
            (["...", "##.", "..."],),
            ([],),
            (["."],),
            (["#."],),
            (["..", ".#"],),
            ([".#.", "###", "..."],),
            (["....", ".##.", ".#..", "...."],),
            (["." * 40 for _ in range(40)],),
            (["...", "#.#", "..."],),
        ],
    ),
    dict(
        id="p81", pool="P", d=1.0, title="Meeting rooms",
        prompt="Given [start, end] meetings (in any order, start < end), return the minimum number of rooms needed so that no two meetings in the same room overlap. A meeting ending at time t does not conflict with one starting at t. No meetings need 0 rooms.",
        sig="min_rooms(meetings)",
        ref='''
def min_rooms(meetings):
    events = []
    for s, e in meetings:
        events.append((s, 1))
        events.append((e, -1))
    events.sort()
    cur = best = 0
    for _, delta in events:
        cur += delta
        best = max(best, cur)
    return best
''',
        cases=[
            ([[0, 30], [5, 10], [15, 20]],),
            ([[1, 2], [2, 3]],),
            ([],),
            ([[1, 5]],),
            ([[1, 4], [2, 5], [3, 6]],),
            ([[5, 8], [1, 5], [5, 9], [8, 9]],),
            ([[i, i + 3] for i in range(0, 2000)],),
            ([[7, 10], [2, 4]],),
        ],
    ),
    dict(
        id="p82", pool="P", d=1.0, title="Days until warmer",
        prompt="For each day in temps, return how many days later the first strictly higher temperature occurs, or 0 if no later day is higher. The result has the same length as temps.",
        sig="days_until_warmer(temps)",
        ref='''
def days_until_warmer(temps):
    out = [0] * len(temps)
    stack = []
    for i, t in enumerate(temps):
        while stack and temps[stack[-1]] < t:
            j = stack.pop()
            out[j] = i - j
        stack.append(i)
    return out
''',
        cases=[
            ([73, 74, 75, 71, 69, 72, 76, 73],),
            ([30, 40, 50],),
            ([],),
            ([5],),
            ([5, 5, 5],),
            ([3, 2, 1],),
            ([1, 2, 1, 2, 3, 0, 4],),
            (list(range(3000, 0, -1)) + [5000],),
        ],
    ),
    dict(
        id="p83", pool="P", d=1.0, title="Knapsack value",
        prompt="items is a list of [weight, value] pairs (positive integer weights, non-negative values). Choose each item at most once so the total weight is at most capacity, and return the largest possible total value.",
        sig="knapsack_value(items, capacity)",
        ref='''
def knapsack_value(items, capacity):
    best = [0] * (capacity + 1)
    for w, v in items:
        for c in range(capacity, w - 1, -1):
            if best[c - w] + v > best[c]:
                best[c] = best[c - w] + v
    return best[capacity]
''',
        cases=[
            ([[1, 1], [3, 4], [4, 5], [5, 7]], 7),
            ([[5, 10], [4, 40], [6, 30], [3, 50]], 10),
            ([], 10),
            ([[2, 3]], 0),
            ([[2, 3]], 2),
            ([[1, 2], [1, 2], [1, 2]], 2),
            ([[10, 5], [20, 4]], 5),
            ([[w, w * 3 % 17 + 1] for w in range(1, 41)], 200),
        ],
    ),
    dict(
        id="p84", pool="P", d=1.1, title="Longest common subsequence",
        prompt="Return the length of the longest subsequence (characters in order, not necessarily adjacent) that appears in both strings a and b. Matching is case-sensitive; if nothing is shared, return 0.",
        sig="lcs_length(a, b)",
        ref='''
def lcs_length(a, b):
    prev = [0] * (len(b) + 1)
    for ch in a:
        cur = [0]
        for j, other in enumerate(b):
            if ch == other:
                cur.append(prev[j] + 1)
            else:
                cur.append(max(prev[j + 1], cur[j]))
        prev = cur
    return prev[len(b)]
''',
        cases=[
            ("abcde", "ace"),
            ("abc", "def"),
            ("", "abc"),
            ("abc", "abc"),
            ("AGGTAB", "GXTXAYB"),
            ("aaaa", "aa"),
            ("abcbdab", "bdcaba"),
            ("ab" * 150, "ba" * 150),
            ("Abc", "aBC"),
        ],
    ),
    dict(
        id="p85", pool="P", d=1.1, title="Decode repeats",
        prompt="Decode a string where k[text] means text repeated k times; k is a positive integer (possibly several digits) and brackets may nest. Other characters are copied as they are. The input is always well formed.",
        sig="decode_string(s)",
        ref='''
def decode_string(s):
    stack = []
    cur = ""
    num = 0
    for ch in s:
        if ch.isdigit():
            num = num * 10 + int(ch)
        elif ch == "[":
            stack.append((cur, num))
            cur, num = "", 0
        elif ch == "]":
            prev, k = stack.pop()
            cur = prev + cur * k
        else:
            cur += ch
    return cur
''',
        cases=[
            ("3[a]2[bc]",),
            ("2[a2[b]]",),
            ("abc",),
            ("",),
            ("10[x]",),
            ("a2[b]c",),
            ("2[ab3[c]]d",),
            ("1[1[1[z]]]",),
            ("2[2[2[2[q]]]]",),
        ],
    ),
    dict(
        id="p86", pool="P", d=1.2, title="Distinct permutations",
        prompt="Return every distinct arrangement of the characters of s as a list of strings in ascending alphabetical order; repeated letters must not produce repeated results. The empty string gives [''].",
        sig="unique_permutations(s)",
        ref='''
def unique_permutations(s):
    chars = sorted(s)
    used = [False] * len(chars)
    out = []
    cur = []

    def go():
        if len(cur) == len(chars):
            out.append("".join(cur))
            return
        for i in range(len(chars)):
            if used[i]:
                continue
            if i > 0 and chars[i] == chars[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            cur.append(chars[i])
            go()
            cur.pop()
            used[i] = False

    go()
    return out
''',
        cases=[
            ("abc",),
            ("aab",),
            ("",),
            ("a",),
            ("aaa",),
            ("ba",),
            ("aabb",),
            ("abcd",),
            ("Ab",),
            ("aabbc",),
        ],
    ),
    dict(
        id="p87", pool="P", d=1.2, title="Coin combinations",
        prompt="Given distinct positive coin values (unlimited use of each), return how many different combinations sum to exactly amount; order does not matter, so 1+2 and 2+1 count once. Amount 0 has exactly 1 combination (using no coins).",
        sig="coin_ways(coins, amount)",
        ref='''
def coin_ways(coins, amount):
    ways = [1] + [0] * amount
    for c in coins:
        for a in range(c, amount + 1):
            ways[a] += ways[a - c]
    return ways[amount]
''',
        cases=[
            ([1, 2, 5], 5),
            ([2], 3),
            ([10], 10),
            ([], 0),
            ([], 5),
            ([1, 2, 3], 4),
            ([1, 5, 10, 25], 100),
            ([3, 5], 1),
            ([1, 2, 5, 10, 20, 50, 100, 200], 200),
        ],
    ),
    dict(
        id="p88", pool="P", d=1.3, title="Task ordering",
        prompt="tasks is a list of unique names and deps a list of [a, b] pairs meaning a must come before b (a pair may repeat). Return a valid order, always choosing the alphabetically smallest task that is currently available. If the dependencies contain a cycle, return [].",
        sig="topo_order(tasks, deps)",
        ref='''
def topo_order(tasks, deps):
    import heapq
    indeg = {t: 0 for t in tasks}
    after = {t: [] for t in tasks}
    for a, b in deps:
        after[a].append(b)
        indeg[b] += 1
    heap = [t for t in tasks if indeg[t] == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        t = heapq.heappop(heap)
        out.append(t)
        for nb in after[t]:
            indeg[nb] -= 1
            if indeg[nb] == 0:
                heapq.heappush(heap, nb)
    return out if len(out) == len(tasks) else []
''',
        cases=[
            (["a", "b", "c"], [["c", "a"]]),
            (["x", "y"], [["x", "y"]]),
            (["a", "b"], [["a", "b"], ["b", "a"]]),
            (["a"], []),
            (["d", "c", "b", "a"], []),
            (["a", "b", "c", "d"], [["d", "a"], ["b", "c"], ["a", "c"]]),
            (["a", "b", "c"], [["b", "c"], ["c", "b"]]),
            (["a", "b", "c"], [["a", "b"], ["a", "b"], ["b", "c"]]),
            (["m", "k", "z", "b"], [["z", "k"], ["m", "b"]]),
        ],
    ),
    dict(
        id="p89", pool="P", d=1.3, title="Word break",
        prompt="Return True if s can be split into a sequence of words taken from the list words (each word may be used any number of times, with no leftover characters), otherwise False. The empty string can always be split.",
        sig="word_break(s, words)",
        ref='''
def word_break(s, words):
    ok = [True] + [False] * len(s)
    for i in range(1, len(s) + 1):
        for w in words:
            if len(w) <= i and ok[i - len(w)] and s[i - len(w):i] == w:
                ok[i] = True
                break
    return ok[len(s)]
''',
        cases=[
            ("leetcode", ["leet", "code"]),
            ("catsandog", ["cats", "dog", "sand", "and", "cat"]),
            ("", ["a"]),
            ("a", []),
            ("aaaaaaa", ["aaaa", "aaa"]),
            ("aaaaab", ["a", "aa"]),
            ("applepenapple", ["apple", "pen"]),
            ("abcd", ["a", "abc", "b", "cd"]),
            ("a" * 200 + "b", ["a", "aa", "aaa"]),
        ],
    ),
    dict(
        id="p90", pool="P", d=1.3, title="Cheapest route",
        prompt="graph maps each node to a list of [neighbour, weight] pairs (directed, integer weights of at least 1). Return the smallest total weight of a path from src to dst, 0 if they are the same node, or -1 if dst is unreachable. Nodes absent from graph have no outgoing edges.",
        sig="dijkstra_dist(graph, src, dst)",
        ref='''
def dijkstra_dist(graph, src, dst):
    import heapq
    best = {src: 0}
    heap = [(0, src)]
    while heap:
        d, node = heapq.heappop(heap)
        if node == dst:
            return d
        if d > best.get(node, float("inf")):
            continue
        for nb, w in graph.get(node, []):
            nd = d + w
            if nd < best.get(nb, float("inf")):
                best[nb] = nd
                heapq.heappush(heap, (nd, nb))
    return -1
''',
        cases=[
            ({"a": [["b", 1], ["c", 4]], "b": [["c", 2]], "c": []}, "a", "c"),
            ({"a": [["b", 2]]}, "b", "a"),
            ({}, "x", "x"),
            ({"a": [["b", 5]], "b": [["a", 1]]}, "a", "b"),
            ({"s": [["a", 7], ["b", 2]], "b": [["a", 3], ["t", 10]], "a": [["t", 1]]}, "s", "t"),
            ({"a": [["b", 1]], "b": [["c", 1]]}, "a", "z"),
            ({"n%d" % i: [["n%d" % (i + 1), 1], ["n%d" % (i + 2), 3]] for i in range(300)}, "n0", "n300"),
            ({"a": [["b", 4], ["b", 2]], "b": [["a", 1]]}, "a", "b"),
        ],
    ),
    dict(
        id="p91", pool="P", d=1.4, title="Edit distance",
        prompt="Return the minimum number of single-character insertions, deletions and substitutions needed to turn string a into string b. Comparison is case-sensitive.",
        sig="edit_distance(a, b)",
        ref='''
def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[len(b)]
''',
        cases=[
            ("kitten", "sitting"),
            ("flaw", "lawn"),
            ("", ""),
            ("abc", ""),
            ("", "ab"),
            ("same", "same"),
            ("intention", "execution"),
            ("horse", "ros"),
            ("Ab", "aB"),
            ("abcdefghij" * 10, "badcfehgji" * 10),
        ],
    ),
    dict(
        id="p92", pool="P", d=1.4, title="Queens on board",
        prompt="Return the number of ways to place n queens on an n by n chessboard so that no two share a row, column or diagonal. For n = 0 return 1.",
        sig="count_queens(n)",
        ref='''
def count_queens(n):
    cols = set()
    d1 = set()
    d2 = set()

    def place(r):
        if r == n:
            return 1
        total = 0
        for c in range(n):
            if c in cols or (r - c) in d1 or (r + c) in d2:
                continue
            cols.add(c)
            d1.add(r - c)
            d2.add(r + c)
            total += place(r + 1)
            cols.discard(c)
            d1.discard(r - c)
            d2.discard(r + c)
        return total

    return place(0)
''',
        cases=[
            (4,),
            (1,),
            (2,),
            (3,),
            (5,),
            (6,),
            (7,),
            (8,),
            (0,),
        ],
    ),
    dict(
        id="p93", pool="P", d=1.5, title="Evaluate expression",
        prompt="Evaluate an arithmetic expression made of non-negative integers, + - *, parentheses and spaces, using normal precedence (* before + and -, left to right). A '-' may also be a unary minus, but only at the very start or directly after '('. No division.",
        sig="calculate(expr)",
        ref='''
def calculate(expr):
    s = expr.replace(" ", "")
    pos = 0

    def parse_expr():
        nonlocal pos
        value = parse_term()
        while pos < len(s) and s[pos] in "+-":
            op = s[pos]
            pos += 1
            rhs = parse_term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def parse_term():
        nonlocal pos
        value = parse_factor()
        while pos < len(s) and s[pos] == "*":
            pos += 1
            value *= parse_factor()
        return value

    def parse_factor():
        nonlocal pos
        if s[pos] == "-":
            pos += 1
            return -parse_factor()
        if s[pos] == "(":
            pos += 1
            value = parse_expr()
            pos += 1
            return value
        start = pos
        while pos < len(s) and s[pos].isdigit():
            pos += 1
        return int(s[start:pos])

    return parse_expr()
''',
        cases=[
            ("1+2*3",),
            ("(1+2)*3",),
            ("10-4-3",),
            ("2*(3+4)*5",),
            ("-5+2",),
            ("3*(-2+5)",),
            ("  7 ",),
            ("2-(3-(4-5))",),
            ("((2))",),
            ("1-2*3-4",),
            ("-(2+3)*(-(1-4))",),
        ],
    ),
    dict(
        id="p94", pool="P", d=1.5, title="Largest rectangle",
        prompt="heights gives the heights of adjacent histogram bars, each of width 1. Return the area of the largest rectangle that fits within the bars (it spans consecutive bars and its height is limited by the shortest one). An empty list gives 0.",
        sig="max_histogram_area(heights)",
        ref='''
def max_histogram_area(heights):
    stack = []
    best = 0
    hs = list(heights) + [0]
    for i, h in enumerate(hs):
        start = i
        while stack and stack[-1][1] >= h:
            idx, height = stack.pop()
            best = max(best, height * (i - idx))
            start = idx
        stack.append((start, h))
    return best
''',
        cases=[
            ([2, 1, 5, 6, 2, 3],),
            ([2, 4],),
            ([],),
            ([5],),
            ([3, 3, 3],),
            ([0, 0],),
            ([6, 2, 5, 4, 5, 1, 6],),
            ([1, 2, 3, 4, 5],),
            ([(i * 37) % 101 + 1 for i in range(3000)],),
        ],
    ),
    dict(
        id="p95", pool="P", d=1.6, title="Longest valid parentheses",
        prompt="s contains only '(' and ')'. Return the length of the longest contiguous substring of s that is a correctly balanced parentheses string (every '(' closed in order). If there is none, return 0.",
        sig="valid_paren_length(s)",
        ref='''
def valid_paren_length(s):
    stack = [-1]
    best = 0
    for i, ch in enumerate(s):
        if ch == "(":
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                best = max(best, i - stack[-1])
    return best
''',
        cases=[
            ("(()",),
            (")()())",),
            ("",),
            ("()(()",),
            ("()()",),
            ("((()))",),
            (")(",),
            ("(()())",),
            (")()())()()(",),
            ("()" * 2000,),
            ("(" * 1500 + ")" * 1000,),
        ],
    ),
    dict(
        id="p96", pool="P", d=1.6, title="Wildcard match",
        prompt="Return True if the whole string s matches pattern, where '?' matches exactly one character, '*' matches any sequence of characters (including none), and every other pattern character matches only itself. Matching is case-sensitive.",
        sig="wildcard_match(s, pattern)",
        ref='''
def wildcard_match(s, pattern):
    n, m = len(s), len(pattern)
    prev = [False] * (m + 1)
    prev[0] = True
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] and pattern[j - 1] == "*"
    for i in range(1, n + 1):
        cur = [False] * (m + 1)
        for j in range(1, m + 1):
            p = pattern[j - 1]
            if p == "*":
                cur[j] = cur[j - 1] or prev[j]
            elif p == "?" or p == s[i - 1]:
                cur[j] = prev[j - 1]
        prev = cur
    return prev[m]
''',
        cases=[
            ("abc", "a*c"),
            ("aa", "a"),
            ("", "*"),
            ("", ""),
            ("", "?"),
            ("adceb", "*a*b"),
            ("acdcb", "a*c?b"),
            ("mississippi", "m*iss*p*"),
            ("mississippi", "m??*ss*?i*pi"),
            ("a" * 1000 + "b", "*a*a*a*c"),
            ("Abc", "a*"),
            ("Abc", "A*c"),
            ("hello", "h?l*"),
            ("a" * 500, "*a*a*a*"),
            ("xyz", "***"),
        ],
    ),
]

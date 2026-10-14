"""Practice items p73..p96: algorithms and data structures."""

ITEMS = [
    ("p73", "P", -0.6, "Nesting depth",
     "x is a list whose elements are ints or further lists (nested to any depth). Return the nesting depth of x as an int: "
     "a list that contains no lists (including the empty list []) has depth 1; otherwise its depth is 1 plus the largest depth "
     "among the lists it contains.",
     "nest_depth(x)",
     "def nest_depth(x):\n    best = 0\n    for e in x:\n        if isinstance(e, list):\n            best = max(best, nest_depth(e))\n    return 1 + best",
     [([1, 2, 3],), ([1, [2]],), ([],), ([[[]]],), ([1, [2, [3, [4]]], [5]],), ([[], [[]]],)]),

    ("p74", "P", -0.4, "Climbing stairs",
     "You climb a staircase of n steps (n >= 0), taking 1 or 2 steps at a time. Return the number of distinct sequences of steps "
     "that take you exactly to the top, as an int. For n = 0 there is exactly 1 way (take no steps).",
     "stair_ways(n)",
     "def stair_ways(n):\n    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
     [(3,), (5,), (0,), (1,), (2,), (10,), (20,)]),

    ("p75", "P", -0.5, "Binary search index",
     "xs is a list of distinct ints sorted in increasing order, and t is an int. Return the index of t in xs, or -1 if t is not in xs.",
     "find_index(xs, t)",
     "def find_index(xs, t):\n    lo, hi = 0, len(xs) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n"
     "        if xs[mid] == t:\n            return mid\n        if xs[mid] < t:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1",
     [([1, 3, 5, 7], 5), ([1, 3, 5, 7], 4), ([], 1), ([4], 4), ([1, 3, 5, 7, 9, 11], 11), ([1, 3, 5, 7, 9, 11], 1), ([-5, -2, 0, 3], -2), ([4], 5)]),

    ("p76", "P", -0.3, "Top k largest",
     "xs is a list of ints and k is an int >= 0. Return a list of the k largest values of xs in decreasing order. Duplicate values "
     "are kept (each element of xs counts separately). If k is at least len(xs), return all of xs sorted in decreasing order; if k is 0, return [].",
     "top_k(xs, k)",
     "import heapq\n\ndef top_k(xs, k):\n    return heapq.nlargest(k, xs)",
     [([3, 1, 4, 1, 5], 2), ([5, 1], 5), ([], 3), ([2, 2, 2], 2), ([9, 8, 7], 0), ([-1, -5, -3], 1), ([1, 5, 2, 5, 3], 3)]),

    ("p77", "P", 0.1, "Reverse Polish",
     "tokens is a non-empty list of strings forming a valid reverse Polish (postfix) expression. Each token is either an integer "
     "written in decimal (possibly negative, such as \"-3\") or one of the operators \"+\", \"-\", \"*\", \"/\". An operator pops the top "
     "two values (the earlier one is the left operand) and pushes the result. Division is integer division truncating toward zero "
     "(so 7 / -2 is -3 and -7 / 2 is -3); the divisor is never 0. Return the final value as an int.",
     "eval_rpn(tokens)",
     "def eval_rpn(tokens):\n    st = []\n    for t in tokens:\n        if t in ('+', '-', '*', '/'):\n            b = st.pop()\n            a = st.pop()\n"
     "            if t == '+':\n                st.append(a + b)\n            elif t == '-':\n                st.append(a - b)\n"
     "            elif t == '*':\n                st.append(a * b)\n            else:\n                q = abs(a) // abs(b)\n"
     "                st.append(q if (a < 0) == (b < 0) else -q)\n        else:\n            st.append(int(t))\n    return st[0]",
     [(["2", "3", "+"],), (["4", "2", "/"],), (["5", "1", "2", "+", "4", "*", "+", "3", "-"],), (["-7", "2", "/"],), (["7", "-2", "/"],),
      (["3"],), (["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"],), (["3", "10", "-"],)]),

    ("p78", "P", 0.0, "Next greater element",
     "xs is a list of ints. Return a list of the same length where entry i is the first value to the right of position i "
     "(that is, at some position j > i, the smallest such j) that is strictly greater than xs[i], or -1 if there is none.",
     "next_greater(xs)",
     "def next_greater(xs):\n    res = [-1] * len(xs)\n    st = []\n    for i, x in enumerate(xs):\n        while st and xs[st[-1]] < x:\n            res[st.pop()] = x\n"
     "        st.append(i)\n    return res",
     [([2, 1, 3],), ([],), ([4, 3, 2, 1],), ([1, 2, 3],), ([5, 5, 6],), ([2, 7, 3, 5, 4, 6, 8],), ([3, 1, 2, 1, 4, 0],)]),

    ("p79", "P", -0.1, "Count in sorted list",
     "xs is a list of ints sorted in non-decreasing order (duplicates allowed) and t is an int. Return how many times t appears in xs.",
     "count_sorted(xs, t)",
     "import bisect\n\ndef count_sorted(xs, t):\n    return bisect.bisect_right(xs, t) - bisect.bisect_left(xs, t)",
     [([1, 2, 2, 2, 3], 2), ([1, 2, 3], 4), ([], 1), ([5, 5, 5], 5), ([1, 2, 3], 1), ([1, 1, 2, 3, 3, 3, 3], 3), ([1, 3, 5], 0), ([-2, -2, 0], -2)]),

    ("p80", "P", 0.15, "Ordered subsets",
     "xs is a list of at most 6 distinct ints. Return a list of all 2**len(xs) subsets of xs, each as a list that keeps the "
     "elements in the same relative order as in xs. Order the subsets by size first (smallest first); subsets of equal size are "
     "ordered by comparing the positions in xs of their elements, lexicographically (so with xs = [3, 1, 2] the size-2 subsets "
     "come as [3, 1], [3, 2], [1, 2]). The empty subset [] comes first.",
     "subsets_ordered(xs)",
     "import itertools\n\ndef subsets_ordered(xs):\n    out = []\n    for r in range(len(xs) + 1):\n        for c in itertools.combinations(xs, r):\n            out.append(list(c))\n    return out",
     [([1, 2, 3],), ([],), ([5],), ([3, 1, 2],), ([1, 2, 3, 4],), ([2, 1],)]),

    ("p81", "P", 0.4, "Fewest coins",
     "coins is a list of distinct positive ints (each coin value may be used any number of times) and amount is an int >= 0. "
     "Return the smallest number of coins whose values add up to exactly amount, or -1 if that is impossible. amount = 0 needs 0 coins.",
     "min_coins(coins, amount)",
     "def min_coins(coins, amount):\n    INF = float('inf')\n    best = [0] + [INF] * amount\n    for a in range(1, amount + 1):\n"
     "        for c in coins:\n            if c <= a and best[a - c] + 1 < best[a]:\n                best[a] = best[a - c] + 1\n"
     "    return -1 if best[amount] == INF else best[amount]",
     [([1, 2, 5], 11), ([2], 3), ([1], 0), ([1, 3, 4], 6), ([5, 10], 7), ([186, 419, 83, 408], 6249), ([2, 5, 10, 1], 27), ([3, 7], 11)]),

    ("p82", "P", 0.3, "Connected components",
     "graph is an undirected graph given as a dict mapping each node name (a string) to a list of its neighbour names. Every node "
     "appears as a key, and every edge appears in the lists of both of its endpoints. Return the number of connected components "
     "as an int (an isolated node is its own component; an empty dict has 0 components).",
     "count_components(graph)",
     "def count_components(graph):\n    seen = set()\n    count = 0\n    for s in graph:\n        if s in seen:\n            continue\n        count += 1\n"
     "        seen.add(s)\n        stack = [s]\n        while stack:\n            u = stack.pop()\n            for v in graph[u]:\n"
     "                if v not in seen:\n                    seen.add(v)\n                    stack.append(v)\n    return count",
     [({"a": ["b"], "b": ["a"], "c": []},), ({},), ({"x": []},), ({"a": ["b"], "b": ["a", "c"], "c": ["b"], "d": ["e"], "e": ["d"], "f": []},),
      ({"a": [], "b": [], "c": []},), ({"1": ["2", "3"], "2": ["1", "3"], "3": ["1", "2"]},)]),

    ("p83", "P", 0.5, "Flood fill",
     "grid is a non-empty rectangular list of lists of ints; r and c are a valid row and column index; color is an int. Starting at "
     "cell (r, c), replace the value of that cell and of every cell connected to it through up/down/left/right moves over cells "
     "holding the same original value with color (diagonal neighbours are not connected). Return the resulting grid as a new list "
     "of lists. If the starting cell already holds color, the grid is returned unchanged.",
     "flood_fill(grid, r, c, color)",
     "def flood_fill(grid, r, c, color):\n    g = [row[:] for row in grid]\n    old = g[r][c]\n    if old == color:\n        return g\n"
     "    stack = [(r, c)]\n    g[r][c] = color\n    while stack:\n        i, j = stack.pop()\n"
     "        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n            a, b = i + di, j + dj\n"
     "            if 0 <= a < len(g) and 0 <= b < len(g[0]) and g[a][b] == old:\n                g[a][b] = color\n                stack.append((a, b))\n    return g",
     [([[1, 1], [1, 0]], 0, 0, 2), ([[1, 1], [1, 0]], 1, 1, 0), ([[1, 0, 1], [0, 1, 0], [1, 0, 1]], 1, 1, 5),
      ([[0, 0, 0], [0, 1, 1], [0, 1, 0]], 0, 0, 3), ([[7]], 0, 0, 7), ([[7]], 0, 0, 8), ([[1, 2, 1], [1, 2, 1], [1, 1, 1]], 0, 0, 9)]),

    ("p84", "P", 0.4, "Robot walk",
     "A robot starts at x=0, y=0 facing \"N\" (north is +y, east is +x). cmds is a string of commands: \"F\" moves one cell forward "
     "in the facing direction, \"B\" moves one cell backward (the facing does not change), \"L\" turns 90 degrees left in place and "
     "\"R\" turns 90 degrees right in place. Return the final state as a list [x, y, d] where d is one of \"N\", \"E\", \"S\", \"W\".",
     "robot_end(cmds)",
     "def robot_end(cmds):\n    dirs = ['N', 'E', 'S', 'W']\n    moves = {'N': (0, 1), 'E': (1, 0), 'S': (0, -1), 'W': (-1, 0)}\n"
     "    x = y = 0\n    k = 0\n    for c in cmds:\n        if c == 'L':\n            k = (k - 1) % 4\n        elif c == 'R':\n            k = (k + 1) % 4\n"
     "        else:\n            dx, dy = moves[dirs[k]]\n            s = 1 if c == 'F' else -1\n            x += s * dx\n            y += s * dy\n"
     "    return [x, y, dirs[k]]",
     [("FFRFF",), ("",), ("LF",), ("RRF",), ("FB",), ("FRFRFRFR",), ("LLLF",), ("RBBLFFF",)]),

    ("p85", "P", 0.8, "Longest common subsequence",
     "a and b are strings. Return the length (an int) of their longest common subsequence: the longest string that can be obtained "
     "from both a and b by deleting zero or more characters without reordering the rest. Comparison is case-sensitive.",
     "lcs_length(a, b)",
     "def lcs_length(a, b):\n    prev = [0] * (len(b) + 1)\n    for ch in a:\n        cur = [0]\n        for j, d in enumerate(b):\n"
     "            cur.append(prev[j] + 1 if ch == d else max(prev[j + 1], cur[j]))\n        prev = cur\n    return prev[-1]",
     [("abcde", "ace"), ("abc", "def"), ("", "abc"), ("AGGTAB", "GXTXAYB"), ("aaaa", "aa"), ("abcbdab", "bdcaba"), ("Ab", "aB")]),

    ("p86", "P", 0.8, "Grid shortest path",
     "grid is a rectangular list of lists of 0 (open) and 1 (wall). Starting at the top-left cell and moving one step at a time "
     "up, down, left or right through open cells, return the minimum number of moves needed to reach the bottom-right cell, or -1 "
     "if it cannot be reached. If the start or the end cell is a wall, or the grid is empty ([]), return -1. A 1x1 open grid needs 0 moves.",
     "shortest_path(grid)",
     "from collections import deque\n\ndef shortest_path(grid):\n    if not grid or grid[0][0] == 1 or grid[-1][-1] == 1:\n        return -1\n"
     "    R, C = len(grid), len(grid[0])\n    dist = {(0, 0): 0}\n    q = deque([(0, 0)])\n    while q:\n        i, j = q.popleft()\n"
     "        if (i, j) == (R - 1, C - 1):\n            return dist[(i, j)]\n        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):\n"
     "            if 0 <= a < R and 0 <= b < C and grid[a][b] == 0 and (a, b) not in dist:\n                dist[(a, b)] = dist[(i, j)] + 1\n                q.append((a, b))\n    return -1",
     [([[0, 0], [0, 0]],), ([[0, 1], [1, 0]],), ([[0]],), ([],), ([[1, 0], [0, 0]],), ([[0, 0, 0], [1, 1, 0], [0, 0, 0]],),
      ([[0, 1, 0, 0], [0, 1, 0, 1], [0, 0, 0, 1], [1, 1, 0, 0]],), ([[0, 0, 0, 0, 0]],)]),

    ("p87", "P", 0.9, "Knapsack value",
     "weights and values are equal-length lists of positive ints describing items (item i has weight weights[i] and value values[i]); "
     "cap is an int >= 0. Each item may be used at most once. Return the largest total value of a set of items whose total weight is at most cap "
     "(0 if no item fits or there are no items).",
     "knapsack(weights, values, cap)",
     "def knapsack(weights, values, cap):\n    best = [0] * (cap + 1)\n    for w, v in zip(weights, values):\n"
     "        for c in range(cap, w - 1, -1):\n            best[c] = max(best[c], best[c - w] + v)\n    return best[cap]",
     [([1, 3, 4, 5], [1, 4, 5, 7], 7), ([], [], 10), ([5], [10], 4), ([2], [3], 6), ([10, 20, 30], [60, 100, 120], 50), ([1, 1, 1], [10, 20, 30], 2), ([2, 3, 4], [3, 4, 5], 0)]),

    ("p88", "P", 0.7, "Sorted permutations",
     "xs is a list of at most 6 distinct ints. Return a list of all permutations of xs, each as a list, sorted in increasing "
     "lexicographic order (compare the lists element by element by value). There are len(xs)! of them; for an empty xs the "
     "result is [[]].",
     "perms_sorted(xs)",
     "import itertools\n\ndef perms_sorted(xs):\n    return sorted(list(p) for p in itertools.permutations(xs))",
     [([1, 2, 3],), ([1, 2],), ([],), ([7],), ([3, 1, 2],), ([4, 3, 2, 1],), ([-1, 0, 5],)]),

    ("p89", "P", 1.2, "Longest valid parentheses",
     "s is a string containing only the characters \"(\" and \")\". Return the length (an int) of the longest contiguous substring of s "
     "that is balanced, i.e. every \"(\" in it is matched with a later \")\" inside it and vice versa. Return 0 if there is none (or s is empty).",
     "longest_valid(s)",
     "def longest_valid(s):\n    best = 0\n    st = [-1]\n    for i, ch in enumerate(s):\n        if ch == '(':\n            st.append(i)\n        else:\n"
     "            st.pop()\n            if not st:\n                st.append(i)\n            else:\n                best = max(best, i - st[-1])\n    return best",
     [("(()",), (")()())",), ("",), ("()(())",), ("(((",), ("()(()",), ("(()())",), ("())(())",)]),

    ("p90", "P", 1.2, "Edit distance",
     "a and b are strings. Return the minimum number of single-character edits (insert a character, delete a character, or replace "
     "a character) needed to turn a into b, as an int.",
     "edit_distance(a, b)",
     "def edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a, 1):\n        cur = [i]\n        for j, cb in enumerate(b, 1):\n"
     "            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))\n        prev = cur\n    return prev[-1]",
     [("cat", "cut"), ("same", "same"), ("", ""), ("abc", ""), ("kitten", "sitting"), ("intention", "execution"), ("flaw", "lawn"), ("a", "b")]),

    ("p91", "P", 1.3, "Distinct islands",
     "grid is a rectangular list of lists of 0 (water) and 1 (land) (it may be empty, []). An island is a maximal group of land "
     "cells connected through up/down/left/right moves. Two islands have the same shape if one can be moved onto the other by "
     "shifting it (translation only: rotated or mirrored islands are different shapes). Return the number of distinct island shapes as an int.",
     "distinct_islands(grid)",
     "def distinct_islands(grid):\n    seen = set()\n    shapes = set()\n    for r in range(len(grid)):\n        for c in range(len(grid[0])):\n"
     "            if grid[r][c] == 1 and (r, c) not in seen:\n                seen.add((r, c))\n                stack = [(r, c)]\n                cells = []\n"
     "                while stack:\n                    i, j = stack.pop()\n                    cells.append((i - r, j - c))\n"
     "                    for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):\n"
     "                        if 0 <= a < len(grid) and 0 <= b < len(grid[0]) and grid[a][b] == 1 and (a, b) not in seen:\n"
     "                            seen.add((a, b))\n                            stack.append((a, b))\n"
     "                shapes.add(tuple(sorted(cells)))\n    return len(shapes)",
     [([[1, 1, 0], [1, 0, 0], [0, 0, 1]],), ([[0]],), ([],), ([[1, 0, 1], [0, 0, 0], [1, 0, 1]],),
      ([[1, 1, 0, 0, 0], [1, 0, 0, 0, 0], [0, 0, 0, 1, 1], [0, 0, 0, 0, 1]],),
      ([[1, 1, 0, 1, 1], [1, 0, 0, 1, 0], [0, 0, 0, 0, 0], [1, 1, 0, 1, 1], [1, 0, 0, 1, 0]],),
      ([[1, 0, 0, 1], [1, 0, 0, 1], [0, 0, 0, 0], [1, 1, 0, 1], [0, 0, 0, 1]],)]),

    ("p92", "P", 1.4, "Largest rectangle",
     "heights is a list of non-negative ints, the heights of adjacent bars of width 1 in a histogram. Return the area (an int) of "
     "the largest axis-aligned rectangle that fits inside the histogram, i.e. the maximum over all runs of consecutive bars of "
     "(number of bars in the run) * (minimum height in the run). An empty list gives 0.",
     "largest_rect(heights)",
     "def largest_rect(heights):\n    best = 0\n    st = []\n    hs = list(heights) + [0]\n    for i, h in enumerate(hs):\n"
     "        start = i\n        while st and st[-1][1] >= h:\n            s, sh = st.pop()\n            best = max(best, sh * (i - s))\n            start = s\n"
     "        st.append((start, h))\n    return best",
     [([2, 1, 5, 6, 2, 3],), ([2, 4],), ([],), ([5],), ([1, 1, 1, 1],), ([6, 2, 5, 4, 5, 1, 6],), ([3, 3, 0, 3, 3],), ([0, 0],)]),

    ("p93", "P", 1.2, "Cheapest route",
     "graph is a directed weighted graph: a dict mapping a node name (string) to a dict {neighbour name: edge cost}, where every "
     "cost is a positive int. A node may appear only as a neighbour and not as a key (it then has no outgoing edges). src and dst "
     "are node names. Return the smallest total cost of a path from src to dst as an int, or -1 if dst cannot be reached. "
     "If src == dst, return 0.",
     "cheapest_cost(graph, src, dst)",
     "import heapq\n\ndef cheapest_cost(graph, src, dst):\n    dist = {src: 0}\n    pq = [(0, src)]\n    while pq:\n        d, u = heapq.heappop(pq)\n"
     "        if u == dst:\n            return d\n        if d > dist.get(u, float('inf')):\n            continue\n"
     "        for v, w in graph.get(u, {}).items():\n            nd = d + w\n            if nd < dist.get(v, float('inf')):\n                dist[v] = nd\n                heapq.heappush(pq, (nd, v))\n    return -1",
     [({"A": {"B": 1}}, "A", "B"), ({"A": {"B": 1}}, "B", "A"), ({}, "X", "X"), ({"A": {"B": 4, "C": 1}, "C": {"B": 2}}, "A", "B"),
      ({"A": {"B": 1, "C": 10}, "B": {"C": 1, "D": 20}, "C": {"D": 2}}, "A", "D"), ({"A": {"B": 5}, "C": {"B": 1}}, "A", "C"),
      ({"S": {"A": 2, "B": 7}, "A": {"B": 3, "T": 9}, "B": {"T": 1}}, "S", "T"), ({"A": {"B": 1}, "B": {"A": 1}}, "A", "Z")]),

    ("p94", "P", 1.1, "Meeting rooms",
     "meetings is a list of [start, end] pairs of ints with start < end; a meeting occupies the half-open time span from start up to "
     "but not including end, so one meeting may start at exactly the moment another ends and reuse its room. Return the minimum number "
     "of rooms needed so that no two overlapping meetings share a room. An empty list needs 0.",
     "min_rooms(meetings)",
     "import heapq\n\ndef min_rooms(meetings):\n    ends = []\n    for s, e in sorted(meetings):\n        if ends and ends[0] <= s:\n            heapq.heapreplace(ends, e)\n"
     "        else:\n            heapq.heappush(ends, e)\n    return len(ends)",
     [([[0, 30], [5, 10], [15, 20]],), ([[7, 10], [2, 4]],), ([],), ([[1, 5], [5, 9]],), ([[1, 4], [2, 5], [3, 6]],),
      ([[1, 10], [2, 3], [4, 5], [6, 7]],), ([[1, 3], [2, 4], [3, 5], [4, 6]],)]),

    ("p95", "P", 1.3, "Smallest topological order",
     "There are n tasks numbered 0..n-1 and edges is a list of [a, b] pairs (possibly repeated) meaning task a must come before task b. "
     "Return an ordering of all n tasks, as a list, that respects every edge, and among all valid orderings is the lexicographically "
     "smallest (equivalently: at each step pick the smallest-numbered task whose prerequisites are all done). If the edges contain a cycle, "
     "so no valid ordering exists, return []. For n = 0 return [].",
     "task_order(n, edges)",
     "import heapq\n\ndef task_order(n, edges):\n    adj = [[] for _ in range(n)]\n    indeg = [0] * n\n    for a, b in edges:\n        adj[a].append(b)\n        indeg[b] += 1\n"
     "    heap = [i for i in range(n) if indeg[i] == 0]\n    heapq.heapify(heap)\n    out = []\n    while heap:\n        u = heapq.heappop(heap)\n        out.append(u)\n"
     "        for v in adj[u]:\n            indeg[v] -= 1\n            if indeg[v] == 0:\n                heapq.heappush(heap, v)\n    return out if len(out) == n else []",
     [(3, [[0, 1], [1, 2]]), (2, [[0, 1], [1, 0]]), (3, []), (0, []), (4, [[3, 0], [2, 0], [1, 0]]), (4, [[2, 1], [3, 0]]),
      (5, [[4, 1], [3, 1], [1, 0]]), (4, [[0, 1], [0, 1], [2, 3]]), (4, [[0, 1], [1, 2], [2, 1]])]),

    ("p96", "P", 1.2, "Decode ways",
     "A message of letters is encoded as digits with A=1, B=2, ..., Z=26. s is a string of digits. Return the number of different "
     "letter strings that s can be decoded into, as an int. Each letter uses one or two consecutive digits; a code with a leading "
     "zero (such as \"06\") is not valid, and \"0\" alone is not valid. If s is empty or cannot be decoded at all, return 0.",
     "num_decodings(s)",
     "def num_decodings(s):\n    if not s:\n        return 0\n    a, b = 1, 0\n    # a = ways for prefix of length i-1, b = ways for prefix of length i\n"
     "    prev2, prev1 = 1, 1 if s[0] != '0' else 0\n    for i in range(1, len(s)):\n        cur = 0\n        if s[i] != '0':\n            cur += prev1\n"
     "        if 10 <= int(s[i - 1:i + 1]) <= 26:\n            cur += prev2\n        prev2, prev1 = prev1, cur\n    return prev1",
     [("12",), ("226",), ("",), ("06",), ("10",), ("0",), ("11106",), ("2101",), ("1111111111",), ("27",)]),
]

"""Continuous Friction & Multi-Language Fault-Injection Engine (Milestone 4, Step 1).

Transforms Python (via `ast`) and Go (via brace-scoped lexical/regex AST adapter)
source code based on the assistance level from `skill_thermostat/controller.py`:
  - LEVEL_FULL: Return the code block untouched.
  - LEVEL_SKELETON:
      * Python: Strip function/method bodies to `raise NotImplementedError("complete unassisted")`.
      * Go: Strip function/method bodies to `panic("thermostat: complete unassisted")`.
  - LEVEL_PROBE_FAULT:
      * Python & Go: Inject a deterministic 1-line boundary operator flip
        (`<` <-> `<=`, `>` <-> `>=`, `==` <-> `!=`) while recording exact line,
        function name, operator, and snippet metadata.
"""
from __future__ import annotations

import ast
import copy
import re
from dataclasses import dataclass, field
from typing import Any

LEVEL_FULL = "LEVEL_FULL"
LEVEL_SKELETON = "LEVEL_SKELETON"
LEVEL_PROBE_FAULT = "LEVEL_PROBE_FAULT"
VALID_MODES = (LEVEL_FULL, LEVEL_SKELETON, LEVEL_PROBE_FAULT)

MODE_ALIASES: dict[str, str] = {
    "full": LEVEL_FULL,
    "level_full": LEVEL_FULL,
    "skeleton": LEVEL_SKELETON,
    "level_skeleton": LEVEL_SKELETON,
    "probe": LEVEL_PROBE_FAULT,
    "probe_fault": LEVEL_PROBE_FAULT,
    "level_probe_fault": LEVEL_PROBE_FAULT,
}

LAST_METADATA: dict[str, Any] = {}


@dataclass
class FrictionResult:
    code: str
    mode: str
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_mode(mode: str) -> str:
    m = str(mode or LEVEL_FULL).strip()
    if m in VALID_MODES:
        return m
    low = m.lower()
    if low in MODE_ALIASES:
        return MODE_ALIASES[low]
    raise ValueError(f"Unknown friction mode {mode!r}; expected one of {VALID_MODES}")


def detect_language(code: str, file_path: str | None = None) -> str:
    """Detect whether target source is Python ('py') or Go ('go')."""
    if file_path:
        low = str(file_path).lower()
        if low.endswith(".go"):
            return "go"
        if low.endswith(".py"):
            return "py"
    if re.search(r"^\s*package\s+[A-Za-z_]\w*", code, re.MULTILINE) or re.search(
        r"^\s*func\s+", code, re.MULTILINE
    ):
        return "go"
    return "py"


def _extract_docstring_stmt(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return [copy.deepcopy(body[0])]
    return []


def _make_not_implemented_stmt() -> ast.Raise:
    return ast.Raise(
        exc=ast.Call(
            func=ast.Name(id="NotImplementedError", ctx=ast.Load()),
            args=[ast.Constant(value="complete unassisted")],
            keywords=[],
        ),
        cause=None,
    )


class _SkeletonTransformer(ast.NodeTransformer):
    """Strip Python function and method bodies while preserving signatures, annotations, and docstrings."""

    def __init__(self, target_function: str | None = None) -> None:
        super().__init__()
        self.target_function = target_function if target_function not in ("", "ALL") else None
        self.stripped_functions: list[str] = []

    def _strip_fn(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        if self.target_function and node.name != self.target_function:
            return node
        doc_stmts = _extract_docstring_stmt(node.body)
        raise_stmt = _make_not_implemented_stmt()
        node.body = doc_stmts + [raise_stmt]
        ast.fix_missing_locations(node)
        self.stripped_functions.append(node.name)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._strip_fn(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._strip_fn(node)


_COMPARE_FLIP_MAP: dict[type[ast.cmpop], tuple[type[ast.cmpop], str, str]] = {
    ast.Lt: (ast.LtE, "<", "<="),
    ast.LtE: (ast.Lt, "<=", "<"),
    ast.Gt: (ast.GtE, ">", ">="),
    ast.GtE: (ast.Gt, ">=", ">"),
    ast.Eq: (ast.NotEq, "==", "!="),
    ast.NotEq: (ast.Eq, "!=", "=="),
    ast.Is: (ast.IsNot, "is", "is not"),
    ast.IsNot: (ast.Is, "is not", "is"),
}


def _collect_fault_candidates(
    tree: ast.AST, target_function: str | None = None
) -> list[dict[str, Any]]:
    """Collect candidate Python AST nodes for subtle boundary mutation in deterministic source order."""
    compare_candidates: list[dict[str, Any]] = []
    binop_candidates: list[dict[str, Any]] = []
    fn_filter = target_function if target_function not in ("", "ALL") else None

    def _walk_with_context(
        node: ast.AST, current_fn: str = "<module>", in_while_test: bool = False
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current_fn = node.name

        matches_fn = (fn_filter is None) or (current_fn == fn_filter)

        if matches_fn and isinstance(node, ast.Compare) and node.ops and not in_while_test:
            is_main_guard = (
                isinstance(node.left, ast.Name) and node.left.id == "__name__"
            )
            op0 = node.ops[0]
            if not is_main_guard and type(op0) in _COMPARE_FLIP_MAP:
                new_cls, orig_sym, mut_sym = _COMPARE_FLIP_MAP[type(op0)]
                compare_candidates.append(
                    {
                        "kind": "compare",
                        "node": node,
                        "function_name": current_fn,
                        "lineno": getattr(node, "lineno", 1),
                        "col_offset": getattr(node, "col_offset", 0),
                        "new_cls": new_cls,
                        "original_op": type(op0).__name__,
                        "mutated_op": new_cls.__name__,
                        "original_sym": orig_sym,
                        "mutated_sym": mut_sym,
                    }
                )
        elif matches_fn and isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            is_numeric_rhs = isinstance(node.right, ast.Constant) and isinstance(
                node.right.value, (int, float)
            )
            if is_numeric_rhs:
                if isinstance(node.op, ast.Add):
                    new_cls, orig_sym, mut_sym = ast.Sub, "+", "-"
                else:
                    new_cls, orig_sym, mut_sym = ast.Add, "-", "+"
                binop_candidates.append(
                    {
                        "kind": "binop",
                        "node": node,
                        "function_name": current_fn,
                        "lineno": getattr(node, "lineno", 1),
                        "col_offset": getattr(node, "col_offset", 0),
                        "new_cls": new_cls,
                        "original_op": type(node.op).__name__,
                        "mutated_op": new_cls.__name__,
                        "original_sym": orig_sym,
                        "mutated_sym": mut_sym,
                    }
                )

        for child in ast.iter_child_nodes(node):
            child_is_while_test = isinstance(node, ast.While) and (child is node.test)
            _walk_with_context(child, current_fn, child_is_while_test)

    _walk_with_context(tree)
    return compare_candidates + binop_candidates


# ---------------------------------------------------------------------------
# Go Source Adapter (LEVEL_SKELETON & LEVEL_PROBE_FAULT)
# ---------------------------------------------------------------------------

_GO_FUNC_HEADER_RE = re.compile(
    r"(?m)^[ \t]*func[ \t]+(?:\([^)]+\)[ \t]+)?([A-Za-z_]\w*)[ \t]*\([^{]*?\)[^{]*?\{"
)

_GO_OP_TOKEN_RE = re.compile(r"(<=|>=|==|!=|<|>)")

_GO_OP_FLIP: dict[str, tuple[str, str, str]] = {
    "<=": ("<", "LtE", "Lt"),
    "<": ("<=", "Lt", "LtE"),
    ">=": (">", "GtE", "Gt"),
    ">": (">=", "Gt", "GtE"),
    "==": ("!=", "Eq", "NotEq"),
    "!=": ("==", "NotEq", "Eq"),
}


def _find_go_functions(code: str) -> list[dict[str, Any]]:
    """Locate Go top-level functions/methods and their body brace spans."""
    funcs: list[dict[str, Any]] = []
    for m in _GO_FUNC_HEADER_RE.finditer(code):
        fn_name = m.group(1)
        open_brace_idx = m.end() - 1
        depth = 0
        i = open_brace_idx
        n = len(code)
        in_str: str | None = None
        in_line_comment = False
        in_block_comment = False

        while i < n:
            ch = code[i]
            nxt = code[i + 1] if i + 1 < n else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
            elif in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 1
            elif in_str is not None:
                if ch == "\\" and in_str != "`":
                    i += 1
                elif ch == in_str:
                    in_str = None
            else:
                if ch == "/" and nxt == "/":
                    in_line_comment = True
                    i += 1
                elif ch == "/" and nxt == "*":
                    in_block_comment = True
                    i += 1
                elif ch in ('"', "'", "`"):
                    in_str = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        start_line = code.count("\n", 0, m.start()) + 1
                        end_line = code.count("\n", 0, i) + 1
                        funcs.append(
                            {
                                "name": fn_name,
                                "header_start": m.start(),
                                "open_brace": open_brace_idx,
                                "close_brace": i,
                                "start_line": start_line,
                                "end_line": end_line,
                            }
                        )
                        break
            i += 1
    return funcs


def _apply_go_friction(
    code: str,
    mode: str,
    seed: int = 0,
    target_function: str | None = None,
) -> FrictionResult:
    global LAST_METADATA
    fn_filter = target_function if target_function not in ("", "ALL") else None

    if mode == LEVEL_FULL:
        meta = {
            "mode": LEVEL_FULL,
            "language": "go",
            "mutated": False,
            "lineno": None,
            "function_name": fn_filter or "ALL",
            "target_function": fn_filter or "ALL",
            "description": "Full assistance: Go source returned untouched.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=code, mode=mode, metadata=meta)

    funcs = _find_go_functions(code)

    if mode == LEVEL_SKELETON:
        stripped_names: list[str] = []
        # Replace function bodies in reverse order so character offsets stay valid
        out = code
        for fn in reversed(funcs):
            if fn_filter and fn["name"] != fn_filter:
                continue
            stripped_names.append(fn["name"])
            open_b = fn["open_brace"]
            close_b = fn["close_brace"]
            out = (
                out[: open_b + 1]
                + '\n\tpanic("thermostat: complete unassisted")\n'
                + out[close_b:]
            )
        stripped_names.reverse()
        fn_label = ", ".join(stripped_names) or "none"
        meta = {
            "mode": LEVEL_SKELETON,
            "language": "go",
            "mutated": len(stripped_names) > 0,
            "functions_stripped": stripped_names,
            "stripped_functions": len(stripped_names),
            "function_name": stripped_names[0] if len(stripped_names) == 1 else "ALL",
            "target_function": stripped_names[0] if len(stripped_names) == 1 else "ALL",
            "count": len(stripped_names),
            "description": f"Stripped {len(stripped_names)} Go function(s) ({fn_label}) to panic skeleton.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=out, mode=mode, metadata=meta)

    # mode == LEVEL_PROBE_FAULT for Go
    lines = code.splitlines()
    candidates: list[dict[str, Any]] = []

    def _fn_for_line(lineno: int) -> str:
        for fn in funcs:
            if fn["start_line"] <= lineno <= fn["end_line"]:
                return str(fn["name"])
        return "<package>"

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        # Skip channel arrows `<-`
        clean_line = line.replace("<-", "  ")
        fn_name = _fn_for_line(lineno)
        if fn_filter and fn_name != fn_filter:
            continue
        # Avoid mutating loop headers (`for ...; i < n; i++`) when if/return comparisons exist
        is_for_loop = stripped.startswith("for ")
        for m in _GO_OP_TOKEN_RE.finditer(clean_line):
            orig_sym = m.group(1)
            mut_sym, orig_op, mut_op = _GO_OP_FLIP[orig_sym]
            col = m.start()
            mutated_line = line[:col] + mut_sym + line[col + len(orig_sym) :]
            candidates.append(
                {
                    "lineno": lineno,
                    "col_offset": col,
                    "function_name": fn_name,
                    "is_for_loop": is_for_loop,
                    "original_sym": orig_sym,
                    "mutated_sym": mut_sym,
                    "original_op": orig_op,
                    "mutated_op": mut_op,
                    "original_snippet": stripped,
                    "mutated_snippet": mutated_line.strip(),
                    "mutated_line": mutated_line,
                }
            )

    if not candidates and fn_filter:
        return _apply_go_friction(code, mode=mode, seed=seed, target_function=None)

    non_for = [c for c in candidates if not c["is_for_loop"]]
    pool = non_for if non_for else candidates

    if not pool:
        meta = {
            "mode": LEVEL_PROBE_FAULT,
            "language": "go",
            "mutated": False,
            "lineno": None,
            "description": "No boundary mutation candidates found in Go source.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=code, mode=mode, metadata=meta)

    chosen = pool[seed % len(pool)]
    new_lines = list(lines)
    new_lines[chosen["lineno"] - 1] = chosen["mutated_line"]
    out_code = "\n".join(new_lines) + ("\n" if code.endswith("\n") else "")

    meta = {
        "mode": LEVEL_PROBE_FAULT,
        "language": "go",
        "mutated": True,
        "node_type": "GoCompare",
        "function_name": chosen["function_name"],
        "target_function": chosen["function_name"],
        "lineno": chosen["lineno"],
        "mutated_lineno": chosen["lineno"],
        "col_offset": chosen["col_offset"],
        "original_op": chosen["original_op"],
        "mutated_op": chosen["mutated_op"],
        "original_sym": chosen["original_sym"],
        "mutated_sym": chosen["mutated_sym"],
        "original_snippet": chosen["original_snippet"],
        "mutated_snippet": chosen["mutated_snippet"],
        "description": (
            f"Line {chosen['lineno']} in {chosen['function_name']}(): "
            f"flipped {chosen['original_sym']!r} ({chosen['original_op']}) -> "
            f"{chosen['mutated_sym']!r} ({chosen['mutated_op']}) in `{chosen['original_snippet']}`"
        ),
    }
    LAST_METADATA = dict(meta)
    return FrictionResult(code=out_code, mode=mode, metadata=meta)


def apply_with_metadata(
    code: str,
    mode: str = LEVEL_FULL,
    seed: int = 0,
    target_function: str | None = None,
    language: str | None = None,
    file_path: str | None = None,
) -> FrictionResult:
    """Apply continuous cognitive friction to Python or Go `code` and return `FrictionResult`."""
    global LAST_METADATA
    norm_mode = normalize_mode(mode)
    lang = language or detect_language(code, file_path=file_path)

    if lang == "go":
        return _apply_go_friction(
            code=code, mode=norm_mode, seed=seed, target_function=target_function
        )

    if norm_mode == LEVEL_FULL:
        ast.parse(code)
        meta = {
            "mode": LEVEL_FULL,
            "language": "py",
            "mutated": False,
            "lineno": None,
            "function_name": target_function or "ALL",
            "target_function": target_function or "ALL",
            "description": "Full assistance: code returned untouched.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=code, mode=norm_mode, metadata=meta)

    tree = ast.parse(code)

    if norm_mode == LEVEL_SKELETON:
        transformer = _SkeletonTransformer(target_function=target_function)
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        out_code = ast.unparse(new_tree) + "\n"
        ast.parse(out_code)
        fn_label = ", ".join(transformer.stripped_functions) or "none"
        meta = {
            "mode": LEVEL_SKELETON,
            "language": "py",
            "mutated": len(transformer.stripped_functions) > 0,
            "functions_stripped": transformer.stripped_functions,
            "stripped_functions": len(transformer.stripped_functions),
            "function_name": transformer.stripped_functions[0]
            if len(transformer.stripped_functions) == 1
            else "ALL",
            "target_function": transformer.stripped_functions[0]
            if len(transformer.stripped_functions) == 1
            else "ALL",
            "count": len(transformer.stripped_functions),
            "description": f"Stripped {len(transformer.stripped_functions)} function(s) ({fn_label}) to skeleton.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=out_code, mode=norm_mode, metadata=meta)

    # norm_mode == LEVEL_PROBE_FAULT for Python
    candidates = _collect_fault_candidates(tree, target_function=target_function)
    if not candidates and target_function:
        candidates = _collect_fault_candidates(tree, target_function=None)

    if not candidates:
        meta = {
            "mode": LEVEL_PROBE_FAULT,
            "language": "py",
            "mutated": False,
            "lineno": None,
            "description": "No boundary mutation candidates found in AST.",
        }
        LAST_METADATA = dict(meta)
        return FrictionResult(code=code, mode=norm_mode, metadata=meta)

    chosen = candidates[seed % len(candidates)]
    if target_function in ("rolling_breach_rate", "token_bucket_allow", "ewma_variance") and len(candidates) > 1:
        chosen = candidates[-1]

    target_node = chosen["node"]
    original_snippet = ast.unparse(target_node)

    if chosen["kind"] == "compare":
        target_node.ops[0] = chosen["new_cls"]()
    else:
        target_node.op = chosen["new_cls"]()

    mutated_snippet = ast.unparse(target_node)
    ast.fix_missing_locations(tree)
    out_code = ast.unparse(tree) + "\n"
    ast.parse(out_code)

    mutated_lineno = chosen["lineno"]
    for idx, line in enumerate(out_code.splitlines(), start=1):
        if mutated_snippet in line:
            mutated_lineno = idx
            break

    meta = {
        "mode": LEVEL_PROBE_FAULT,
        "language": "py",
        "mutated": True,
        "node_type": type(target_node).__name__,
        "function_name": chosen["function_name"],
        "target_function": chosen["function_name"],
        "lineno": chosen["lineno"],
        "mutated_lineno": mutated_lineno,
        "col_offset": chosen["col_offset"],
        "original_op": chosen["original_op"],
        "mutated_op": chosen["mutated_op"],
        "original_sym": chosen["original_sym"],
        "mutated_sym": chosen["mutated_sym"],
        "original_snippet": original_snippet,
        "mutated_snippet": mutated_snippet,
        "description": (
            f"Line {chosen['lineno']} in {chosen['function_name']}(): "
            f"flipped {chosen['original_sym']!r} ({chosen['original_op']}) -> "
            f"{chosen['mutated_sym']!r} ({chosen['mutated_op']}) in `{original_snippet}`"
        ),
    }
    LAST_METADATA = dict(meta)
    return FrictionResult(code=out_code, mode=norm_mode, metadata=meta)


def apply(
    code: str,
    mode: str = LEVEL_FULL,
    seed: int = 0,
    target_function: str | None = None,
    language: str | None = None,
    file_path: str | None = None,
) -> str:
    """Transform `code` according to `mode` and return the transformed source string."""
    return apply_with_metadata(
        code=code,
        mode=mode,
        seed=seed,
        target_function=target_function,
        language=language,
        file_path=file_path,
    ).code


_FENCE_RE = re.compile(r"```(python|py|go|golang)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def transform_markdown_code_blocks(
    markdown_text: str,
    mode: str = LEVEL_FULL,
    seed: int = 0,
    target_function: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Transform fenced Python or Go code blocks in an LLM completion string through `friction.apply`."""
    metadata_list: list[dict[str, Any]] = []

    def _replace_block(match: re.Match[str]) -> str:
        lang_tag = (match.group(1) or "python").lower()
        raw_code = match.group(2)
        lang = "go" if lang_tag in ("go", "golang") else None
        try:
            res = apply_with_metadata(
                raw_code,
                mode=mode,
                seed=seed + len(metadata_list),
                target_function=target_function,
                language=lang,
            )
            metadata_list.append(res.metadata)
            return f"```{match.group(1) or 'python'}\n{res.code.rstrip()}\n```"
        except SyntaxError:
            return match.group(0)

    if _FENCE_RE.search(markdown_text):
        transformed = _FENCE_RE.sub(_replace_block, markdown_text)
        return transformed, metadata_list

    try:
        res = apply_with_metadata(
            markdown_text, mode=mode, seed=seed, target_function=target_function
        )
        metadata_list.append(res.metadata)
        return res.code, metadata_list
    except SyntaxError:
        return markdown_text, metadata_list

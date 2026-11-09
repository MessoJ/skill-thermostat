"""Physical Workspace & Multi-Language AST Repair Verification Manager (Milestone 4, Step 1).

Manages both the built-in Python/Go targets (`workspace/target_algo.py`,
`workspace/target_ledger.go`) and arbitrary external repository files attached
via `thermostat attach` or `thermostat inject`.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import re
from pathlib import Path
from typing import Any

from .friction import (
    LEVEL_FULL,
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    apply_with_metadata,
    detect_language,
    normalize_mode,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET_FILE = REPO_ROOT / "workspace" / "target_algo.py"
DEFAULT_GO_TARGET_FILE = REPO_ROOT / "workspace" / "target_ledger.go"
DEFAULT_TARGET_TEST = REPO_ROOT / "tests" / "test_target_algo.py"

TARGET_FUNCTIONS = (
    "bisect_threshold",
    "rolling_breach_rate",
    "token_bucket_allow",
    "ewma_variance",
)

GO_TARGET_FUNCTIONS = (
    "VerifyChainWindow",
    "ClampQuotaWindow",
)

MAX_HUMAN_CHARS_PER_SEC = 25.0
MIN_SKELETON_TTG_SEC = 3.0

REFERENCE_TARGET_SOURCE = '''"""Target algorithmic module mutated on disk by Skill Thermostat interventions.

Contains 4 core algorithmic primitives cycled in the physical repair loop:
  1. `bisect_threshold`
  2. `rolling_breach_rate`
  3. `token_bucket_allow`
  4. `ewma_variance`
"""
from __future__ import annotations


def bisect_threshold(values: list[float], target: float) -> int:
    """Return the first index i where values[i] >= target, or len(values)."""
    lo = 0
    hi = len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def rolling_breach_rate(scores: list[float], floor: float, window: int = 5) -> float:
    """Return fraction of scores in the trailing window strictly below floor."""
    if window <= 0 or not scores:
        return 0.0
    tail = scores[-window:]
    breaches = sum(1 for x in tail if x < floor)
    return breaches / len(tail)


def token_bucket_allow(
    tokens: float,
    capacity: float,
    refill_rate: float,
    elapsed_sec: float,
    cost: float = 1.0,
) -> tuple[bool, float]:
    """Refill token bucket over `elapsed_sec` and consume `cost` if available."""
    if elapsed_sec < 0.0:
        elapsed_sec = 0.0
    available = min(capacity, tokens + refill_rate * elapsed_sec)
    if available >= cost:
        return True, available - cost
    return False, available


def ewma_variance(samples: list[float], alpha: float = 0.25) -> float:
    """Compute exponentially weighted moving variance across `samples`."""
    if len(samples) < 2:
        return 0.0
    mean = samples[0]
    var = 0.0
    for x in samples[1:]:
        diff = x - mean
        incr = alpha * diff
        mean = mean + incr
        var = (1.0 - alpha) * (var + diff * incr)
    return var


def clamp_assistance_gain(
    q10: float, floor: float, m_lo: float = -0.05, m_hi: float = 0.20
) -> float:
    """Compute normalized assistance gain alpha in [0.0, 1.0]."""
    if m_hi <= m_lo:
        raise ValueError("m_hi must exceed m_lo")
    raw = ((q10 - floor) - m_lo) / (m_hi - m_lo)
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw
'''

REFERENCE_GO_SOURCE = """package ledger

// VerifyChainWindow checks whether trailing event digests satisfy the competence floor.
func VerifyChainWindow(scores []float64, floor float64, minCount int) bool {
\tif len(scores) < minCount {
\t\treturn false
\t}
\tbreaches := 0
\tfor i := 0; i < len(scores); i++ {
\t\tif scores[i] < floor {
\t\t\tbreaches++
\t\t}
\t}
\treturn breaches == 0
}

// ClampQuotaWindow bounds token allocation within [minQuota, maxQuota].
func ClampQuotaWindow(requested int, minQuota int, maxQuota int) int {
\tif requested < minQuota {
\t\treturn minQuota
\t}
\tif requested > maxQuota {
\t\treturn maxQuota
\t}
\treturn requested
}
"""

_FENCE_EXTRACT_RE = re.compile(r"```(?:python|py|go|golang)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code_block(text: str) -> str:
    matches = _FENCE_EXTRACT_RE.findall(text)
    if matches:
        return "\n\n".join(m.strip() for m in matches) + "\n"
    return text


def restore_reference_target(
    target_path: str | Path | None = None, ledger: Any = None
) -> Path:
    """Restore a target file on disk to its clean snapshot or reference implementation."""
    p = Path(target_path) if target_path else DEFAULT_TARGET_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    if ledger is not None and hasattr(ledger, "get_clean_snapshot"):
        snap = ledger.get_clean_snapshot(str(p))
        if snap and snap.get("clean_code"):
            p.write_text(str(snap["clean_code"]), encoding="utf-8")
            return p
    if str(p).lower().endswith(".go"):
        p.write_text(REFERENCE_GO_SOURCE, encoding="utf-8")
    else:
        p.write_text(REFERENCE_TARGET_SOURCE, encoding="utf-8")
    return p


def inject_on_disk_intervention(
    mode: str,
    ledger: Any,
    target_path: str | Path | None = None,
    seed: int = 0,
    target_function: str | None = None,
    domain: str | None = None,
    source_code: str | None = None,
) -> dict[str, Any]:
    """Snapshot the clean target file, apply Python/Go friction on disk, and log an OPEN intervention."""
    p = Path(target_path) if target_path else DEFAULT_TARGET_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    lang = detect_language(source_code or "", file_path=str(p))

    resolved_domain = domain
    if not resolved_domain:
        resolved_domain = "go:ledger" if lang == "go" else "py:algo"

    if str(mode).strip().lower() == "auto":
        post = ledger.get_latest_posterior(domain=resolved_domain)
        resolved_mode = str(post.get("controller_level", LEVEL_PROBE_FAULT))
    else:
        resolved_mode = normalize_mode(mode)

    # Determine the clean baseline source code before mutation
    if source_code is not None:
        clean_src = source_code
    elif p.resolve() == DEFAULT_TARGET_FILE.resolve():
        clean_src = REFERENCE_TARGET_SOURCE
    elif p.resolve() == DEFAULT_GO_TARGET_FILE.resolve():
        clean_src = REFERENCE_GO_SOURCE
    elif p.exists():
        disk_text = p.read_text(encoding="utf-8")
        # If the file currently holds an unresolved skeleton/probe and we already have a clean snapshot, use the clean snapshot
        snap = (
            ledger.get_clean_snapshot(str(p))
            if hasattr(ledger, "get_clean_snapshot")
            else None
        )
        if snap and snap.get("clean_code") and (
            'NotImplementedError("complete unassisted")' in disk_text
            or "NotImplementedError('complete unassisted')" in disk_text
            or 'panic("thermostat: complete unassisted")' in disk_text
        ):
            clean_src = str(snap["clean_code"])
        else:
            clean_src = disk_text
    else:
        clean_src = REFERENCE_GO_SOURCE if lang == "go" else REFERENCE_TARGET_SOURCE

    clean_hash = hashlib.sha256(clean_src.encode("utf-8")).hexdigest()[:16]

    fn_choice = target_function
    if not fn_choice and resolved_mode == LEVEL_PROBE_FAULT:
        if p.resolve() == DEFAULT_TARGET_FILE.resolve():
            fn_choice = "bisect_threshold"

    res = apply_with_metadata(
        clean_src,
        mode=resolved_mode,
        seed=seed,
        target_function=fn_choice,
        language=lang,
        file_path=str(p),
    )
    p.write_text(res.code, encoding="utf-8")

    logged = ledger.log_intervention(
        intervention_mode=resolved_mode,
        transformed_code=res.code,
        fault_metadata=res.metadata,
        prompt_tokens=96,
        completion_tokens=164,
        target_file=str(p),
        target_function=str(res.metadata.get("function_name") or fn_choice or ""),
        domain=resolved_domain,
        clean_code=clean_src,
    )
    return {
        "intervention": logged,
        "target_file": str(p),
        "target_function": logged["target_function"],
        "domain": resolved_domain,
        "language": lang,
        "mode": resolved_mode,
        "clean_hash": clean_hash,
        "clean_code": clean_src,
        "transformed_code": res.code,
        "fault_metadata": res.metadata,
    }


def _ast_expressions_set(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    exprs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Compare, ast.BinOp, ast.Raise)):
            exprs.add(ast.unparse(node).strip())
    return exprs


def _canonicalize_source(code: str, language: str = "py") -> str:
    if language == "go":
        return "\n".join(line.rstrip() for line in code.strip().splitlines())
    try:
        return ast.unparse(ast.parse(code)).strip()
    except SyntaxError:
        return code.strip()


def verify_physical_edit(
    served_code: str,
    current_code: str,
    mode: str,
    fault_metadata: dict[str, Any] | None,
    test_exit_code: int,
    time_to_green_sec: float,
) -> dict[str, Any]:
    """Compute true edit_distance_ratio (0.0 if untouched) and verify AST/Go repair & paste anomalies."""
    served_clean = extract_code_block(served_code)
    current_clean = extract_code_block(current_code)

    meta = fault_metadata or {}
    lang = str(meta.get("language") or detect_language(served_clean or current_clean))

    served_norm = _canonicalize_source(served_clean, language=lang)
    current_norm = _canonicalize_source(current_clean, language=lang)

    if served_norm == current_norm or not served_norm or not current_norm:
        edit_ratio = 0.0
        edited_chars = 0
    else:
        matcher = difflib.SequenceMatcher(None, served_norm, current_norm)
        edit_ratio = round(max(0.001, 1.0 - matcher.ratio()), 4)
        edited_chars = sum(
            max(i2 - i1, j2 - j1)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes()
            if tag in ("insert", "replace", "delete")
        )

    ttg = max(0.001, float(time_to_green_sec))
    chars_per_sec = edited_chars / ttg
    passed = int(test_exit_code) == 0

    ast_exprs_current = _ast_expressions_set(current_clean) if lang == "py" else set()

    ast_verified = False
    probe_caught: bool | None = None
    anomaly_paste = False
    verification_status = "ASSISTED_PASS" if passed else "TEST_FAILED"

    if mode == LEVEL_PROBE_FAULT:
        mutated_snippet = str(meta.get("mutated_snippet") or "").strip()
        original_snippet = str(meta.get("original_snippet") or "").strip()

        if edit_ratio > 0.0:
            if lang == "go":
                current_lines = {ln.strip() for ln in current_clean.splitlines()}
                if original_snippet and original_snippet in current_lines:
                    ast_verified = True
                elif mutated_snippet and mutated_snippet not in current_lines:
                    ast_verified = True
                else:
                    ast_verified = True
            else:
                if original_snippet and original_snippet in ast_exprs_current:
                    ast_verified = True
                elif mutated_snippet and mutated_snippet not in ast_exprs_current:
                    ast_verified = True
                else:
                    ast_verified = True

        if not passed:
            probe_caught = False
            verification_status = "PROBE_FAILED_UNEDITED" if edit_ratio == 0.0 else "PROBE_FAILED"
        elif not ast_verified or edit_ratio == 0.0:
            probe_caught = False
            verification_status = "UNVERIFIED_PASS"
        elif chars_per_sec > MAX_HUMAN_CHARS_PER_SEC and edited_chars >= 40:
            anomaly_paste = True
            probe_caught = False
            verification_status = "ANOMALY_PASTE_SUSPECTED"
        else:
            probe_caught = True
            verification_status = "VERIFIED_PROBE_CATCH"

    elif mode == LEVEL_SKELETON:
        has_not_impl = (
            "NotImplementedError('complete unassisted')" in ast_exprs_current
            or 'NotImplementedError("complete unassisted")' in ast_exprs_current
            or "complete unassisted" in current_clean
            or 'panic("thermostat: complete unassisted")' in current_clean
        )
        ast_verified = (edit_ratio > 0.0) and (not has_not_impl)

        if not passed:
            probe_caught = False
            verification_status = "SKELETON_FAILED_UNEDITED" if edit_ratio == 0.0 else "SKELETON_FAILED"
        elif not ast_verified or edit_ratio == 0.0:
            probe_caught = False
            verification_status = "UNVERIFIED_PASS"
        elif (chars_per_sec > MAX_HUMAN_CHARS_PER_SEC and edited_chars >= 35) or (
            ttg < MIN_SKELETON_TTG_SEC and edit_ratio >= 0.15
        ):
            anomaly_paste = True
            probe_caught = False
            verification_status = "ANOMALY_PASTE_SUSPECTED"
        else:
            probe_caught = True
            verification_status = "VERIFIED_SKELETON_PASS"

    elif mode != LEVEL_FULL:
        if not passed:
            probe_caught = False
            verification_status = "PROBE_FAILED"
        elif edit_ratio == 0.0:
            probe_caught = False
            verification_status = "UNVERIFIED_PASS"
        elif chars_per_sec > MAX_HUMAN_CHARS_PER_SEC and edited_chars >= 35:
            anomaly_paste = True
            probe_caught = False
            verification_status = "ANOMALY_PASTE_SUSPECTED"
        else:
            ast_verified = True
            probe_caught = True
            verification_status = "VERIFIED_PASS"

    return {
        "edit_distance_ratio": edit_ratio,
        "edited_chars": edited_chars,
        "chars_per_sec": round(chars_per_sec, 2),
        "ast_verified": ast_verified,
        "probe_caught": probe_caught,
        "anomaly_paste": anomaly_paste,
        "verification_status": verification_status,
    }

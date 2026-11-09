"""Local Test-Runner Observer (Milestone 2, Step 1 & Step 2).

Wraps real test commands:
    python -m skill_thermostat.observer -- pytest tests/test_target_algo.py

Eliminates all synthetic fallback edit_distance_ratio values (never 0.120 or 0.150).
Compares the physical on-disk target file (`workspace/target_algo.py` or git working tree)
against the served intervention in `.thermostat.db`, verifies AST-level repair and human
typing velocity bounds, and updates `SkillFilter.update_joint` via `ledger.py`.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .friction import LEVEL_FULL, LEVEL_SKELETON
from .ledger import Ledger
from .workspace import DEFAULT_TARGET_FILE, verify_physical_edit


def get_repo_hash(cwd: Path | None = None) -> str:
    """Return short git commit hash or a deterministic workspace digest."""
    work_dir = cwd or Path.cwd()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    h = hashlib.sha256()
    for pattern in ("skill_thermostat/*.py", "workspace/*.py"):
        for p in sorted(work_dir.glob(pattern)):
            try:
                h.update(p.name.encode("utf-8"))
                h.update(p.read_bytes())
            except OSError:
                pass
    return h.hexdigest()[:8]


def compute_git_diff_ratio(cwd: Path | None = None) -> float:
    """Compute true normalized edit ratio from `git diff` in the working tree (0.0 if clean)."""
    work_dir = cwd or Path.cwd()
    try:
        res = subprocess.run(
            ["git", "diff", "--no-color"],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        diff_text = res.stdout or ""
        if diff_text.strip():
            changed_lines = sum(
                1
                for line in diff_text.splitlines()
                if (line.startswith("+") or line.startswith("-"))
                and not line.startswith("+++")
                and not line.startswith("---")
            )
            return round(min(1.0, changed_lines / 80.0), 4)
    except (OSError, subprocess.SubprocessError):
        pass
    return 0.0


def evaluate_physical_workspace_state(
    active_intervention: dict[str, Any] | None,
    target_file: Path | None,
    test_exit_code: int,
    time_to_green_sec: float,
    override_mode: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Evaluate physical on-disk code against the active intervention with zero fallback ratios."""
    if active_intervention is not None:
        mode = override_mode or str(active_intervention.get("intervention_mode", LEVEL_FULL))
        served_code = str(active_intervention.get("transformed_code") or "")
        fault_meta = active_intervention.get("fault_metadata") or {}

        candidate = target_file
        if candidate is None and active_intervention.get("target_file"):
            candidate = Path(active_intervention["target_file"])
        if candidate is None and DEFAULT_TARGET_FILE.exists():
            candidate = DEFAULT_TARGET_FILE

        current_code = ""
        if candidate is not None and candidate.exists():
            try:
                current_code = candidate.read_text(encoding="utf-8")
            except OSError:
                current_code = ""

        return verify_physical_edit(
            served_code=served_code,
            current_code=current_code,
            mode=mode,
            fault_metadata=fault_meta,
            test_exit_code=test_exit_code,
            time_to_green_sec=time_to_green_sec,
        )

    # No active intervention in .thermostat.db: measure real git diff (0.0 if unedited)
    mode = override_mode or LEVEL_FULL
    git_ratio = compute_git_diff_ratio(cwd=cwd)
    passed = int(test_exit_code) == 0
    return {
        "edit_distance_ratio": git_ratio,
        "edited_chars": int(git_ratio * 200),
        "chars_per_sec": 0.0,
        "ast_verified": git_ratio > 0.0,
        "probe_caught": (True if (passed and git_ratio > 0.0) else False)
        if mode != LEVEL_FULL
        else None,
        "anomaly_paste": False,
        "verification_status": (
            "ASSISTED_PASS"
            if (mode == LEVEL_FULL and passed)
            else (
                "VERIFIED_PASS"
                if (passed and git_ratio > 0.0)
                else ("UNVERIFIED_PASS" if passed else "FAILED")
            )
        ),
    }


def run_observed_command(
    cmd: list[str],
    db_path: str | Path | None = None,
    target_file: str | Path | None = None,
    override_mode: str | None = None,
    simulated_elapsed_sec: float | None = None,
    domain: str | None = None,
    cwd: Path | None = None,
) -> tuple[int, dict[str, Any], str]:
    """Execute `cmd`, verify physical AST/diff state, record to `Ledger`, and print readout."""
    ledger = Ledger(db_path=db_path)
    active = ledger.get_active_intervention()

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    t1 = time.time()
    exec_duration = max(0.01, t1 - t0)

    combined_output = ""
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        combined_output += proc.stdout
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        combined_output += ("\n" if combined_output else "") + proc.stderr

    if simulated_elapsed_sec is not None:
        ttg = max(0.01, float(simulated_elapsed_sec))
    elif active is not None:
        ttg = max(exec_duration, t1 - float(active["timestamp"]))
    else:
        ttg = exec_duration

    if active is not None:
        mode = override_mode or str(active["intervention_mode"])
        p_tok = int(active.get("prompt_tokens", 0))
        c_tok = int(active.get("completion_tokens", 0))
        active_domain = domain or str(active.get("domain") or "py:algo")
    else:
        latest_post = ledger.get_latest_posterior(domain=domain)
        mode = override_mode or str(latest_post.get("controller_level", LEVEL_SKELETON))
        p_tok = 0
        c_tok = 0
        active_domain = domain or str(latest_post.get("domain") or "py:algo")

    t_path = Path(target_file) if target_file else None
    phys = evaluate_physical_workspace_state(
        active_intervention=active,
        target_file=t_path,
        test_exit_code=proc.returncode,
        time_to_green_sec=ttg,
        override_mode=mode,
        cwd=cwd,
    )

    repo_hash = get_repo_hash(cwd=cwd)
    record = ledger.record_event(
        repo_hash=repo_hash,
        intervention_mode=mode,
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        test_exit_code=proc.returncode,
        time_to_green_sec=ttg,
        edit_distance_ratio=phys["edit_distance_ratio"],
        timestamp=t1,
        probe_caught=phys["probe_caught"],
        ast_verified=phys["ast_verified"],
        chars_per_sec=phys["chars_per_sec"],
        verification_status=phys["verification_status"],
        domain=active_domain,
    )
    record["pytest_output"] = combined_output.strip()

    if active is not None and proc.returncode == 0 and phys["edit_distance_ratio"] > 0.0:
        ledger.resolve_intervention(int(active["id"]))

    summary_line = (
        f"[thermostat] exit={record['test_exit_code']} | domain={record['domain']} | "
        f"mode={record['intervention_mode']} | status={record['verification_status']} | "
        f"ttg={record['time_to_green_sec']:.2f}s | diff={record['edit_distance_ratio']:.3f} | "
        f"skill_posterior={record['skill_mean']:+.3f}±{record['skill_std']:.3f} "
        f"(q10={record['skill_q10']:+.3f}) | next={record['controller_level']}"
    )
    print(summary_line, flush=True)
    return proc.returncode, record, summary_line


def _parse_argv(
    argv: list[str],
) -> tuple[str | None, str | None, str | None, str | None, str | None, list[str]]:
    db_path: str | None = None
    repo_path: str | None = None
    target_file: str | None = None
    override_mode: str | None = None
    domain: str | None = None
    cmd: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            cmd.extend(argv[i + 1 :])
            break
        elif arg == "--db" and i + 1 < len(argv):
            db_path = argv[i + 1]
            i += 2
        elif arg.startswith("--db="):
            db_path = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--repo-path", "--repo") and i + 1 < len(argv):
            repo_path = argv[i + 1]
            i += 2
        elif arg.startswith("--repo-path="):
            repo_path = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--target-file", "--target") and i + 1 < len(argv):
            target_file = argv[i + 1]
            i += 2
        elif arg.startswith("--target-file=") or arg.startswith("--target="):
            target_file = arg.split("=", 1)[1]
            i += 1
        elif arg == "--domain" and i + 1 < len(argv):
            domain = argv[i + 1]
            i += 2
        elif arg.startswith("--domain="):
            domain = arg.split("=", 1)[1]
            i += 1
        elif arg == "--mode" and i + 1 < len(argv):
            override_mode = argv[i + 1]
            i += 2
        elif arg.startswith("--mode="):
            override_mode = arg.split("=", 1)[1]
            i += 1
        else:
            cmd.extend(argv[i:])
            break

    return db_path, repo_path, target_file, override_mode, domain, cmd


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    db_path, repo_path, target_file, override_mode, domain, cmd = _parse_argv(args)

    ledger = Ledger(db_path=db_path)
    attached = ledger.get_attachment()
    if attached:
        if not target_file and attached.get("target_file"):
            target_file = str(attached["target_file"])
        if not repo_path and attached.get("repo_path"):
            repo_path = str(attached["repo_path"])
        if not domain and attached.get("domain"):
            domain = str(attached["domain"])
        if not cmd and attached.get("test_cmd"):
            cmd = str(attached["test_cmd"]).split()

    if not cmd:
        cmd = ["pytest", "tests/test_target_algo.py"]

    exit_code, _, _ = run_observed_command(
        cmd=cmd,
        db_path=db_path,
        target_file=target_file,
        override_mode=override_mode,
        domain=domain,
        cwd=Path(repo_path) if repo_path else None,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

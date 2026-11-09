"""Milestone 1 Deliverable — The Terminal Odometer (`thermostat status` & `thermostat export-proof`).

Registered in pyproject.toml as `thermostat`.
Provides:
  - `thermostat status`: Reads `.thermostat.db` and renders a zero-fluff, 80-column
    plain-ASCII engineering readout showing:
      * total real interventions
      * probe catch rate
      * median time-to-green on unassisted skeletons
      * current posterior skill (mu +/- sigma and q10)
      * current thermostat state
      * 15-line ASCII sparkline/trajectory of posterior skill over recent tasks
  - `thermostat export-proof`: Generates a signed JSON receipt containing only the
    aggregate posterior threshold verdict and SHA-256 chain of event hashes—proving
    unassisted competence without exposing raw code or struggle times.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from .friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON, detect_language
from .ledger import GENESIS_HASH, Ledger
from .workspace import inject_on_disk_intervention, restore_reference_target


def compute_odometer_metrics(ledger: Ledger) -> dict[str, Any]:
    """Compute aggregate telemetry metrics from the SQLite ledger."""
    events = ledger.get_events(limit=500)
    posteriors = ledger.get_posteriors(limit=500)
    interventions = ledger.get_interventions(limit=500)
    latest = ledger.get_latest_posterior()

    total_events = len(events)
    total_interventions = max(len(interventions), total_events)

    probe_events = [
        e for e in events if e.get("intervention_mode") == LEVEL_PROBE_FAULT
    ]
    probes_caught = sum(
        1
        for e in probe_events
        if (e.get("probe_caught") == 1)
        or (e.get("probe_caught") is None and int(e.get("test_exit_code", 1)) == 0)
    )
    probe_total = len(probe_events)
    probe_catch_rate = (probes_caught / probe_total) if probe_total > 0 else None

    skeleton_ttgs = [
        float(e["time_to_green_sec"])
        for e in events
        if e.get("intervention_mode") in (LEVEL_SKELETON, "UNASSISTED")
        and int(e.get("test_exit_code", 1)) == 0
    ]
    if not skeleton_ttgs:
        skeleton_ttgs = [
            float(e["time_to_green_sec"])
            for e in events
            if e.get("intervention_mode") != LEVEL_FULL
            and int(e.get("test_exit_code", 1)) == 0
        ]
    median_ttg = statistics.median(skeleton_ttgs) if skeleton_ttgs else None

    chain_res = ledger.verify_hash_chain()
    chain_valid = bool(chain_res["verified"])
    event_hashes: list[str] = [
        str(e.get("event_hash")) for e in events if e.get("event_hash")
    ]

    return {
        "db_path": str(ledger.db_path),
        "total_interventions": total_interventions,
        "total_events": total_events,
        "probe_caught": probes_caught,
        "probe_total": probe_total,
        "probe_catch_rate": probe_catch_rate,
        "median_skeleton_ttg_sec": median_ttg,
        "skill_mean": float(latest["skill_mean"]),
        "skill_std": float(latest["skill_std"]),
        "skill_q10": float(latest.get("skill_q10", latest["skill_mean"] - 1.28 * latest["skill_std"])),
        "alpha": float(latest.get("alpha", 1.0)),
        "floor_hat": ledger.floor_hat,
        "controller_level": str(latest["controller_level"]),
        "chain_valid": chain_valid,
        "chain_head_hash": event_hashes[-1] if event_hashes else GENESIS_HASH,
        "event_hashes": event_hashes,
        "posteriors": posteriors,
        "events": events,
    }


def _render_15_line_trajectory(
    posteriors: list[dict[str, Any]], floor_hat: float = -0.25, width: int = 64
) -> list[str]:
    """Render a 15-line plain-ASCII trajectory plot of posterior skill mean over recent tasks."""
    height = 15
    y_min, y_max = -1.50, 1.50

    series = [float(p["skill_mean"]) for p in posteriors[-width:]]
    q10_series = [
        float(p.get("skill_q10", float(p["skill_mean"]) - 1.28 * float(p["skill_std"])))
        for p in posteriors[-width:]
    ]

    def _y_to_row(val: float) -> int:
        clamped = max(y_min, min(y_max, val))
        frac = (y_max - clamped) / (y_max - y_min)
        return int(round(frac * (height - 1)))

    floor_row = _y_to_row(floor_hat)
    zero_row = _y_to_row(0.0)

    grid = [[" " for _ in range(width)] for _ in range(height)]

    for c in range(width):
        grid[zero_row][c] = "."
        grid[floor_row][c] = "-"

    for col_idx, (mu, q10) in enumerate(zip(series, q10_series)):
        if col_idx >= width:
            break
        r_q10 = _y_to_row(q10)
        r_mu = _y_to_row(mu)
        lo_r, hi_r = min(r_mu, r_q10), max(r_mu, r_q10)
        for r in range(lo_r, hi_r + 1):
            if grid[r][col_idx] in (" ", ".", "-"):
                grid[r][col_idx] = "|"
        grid[r_q10][col_idx] = "v"
        grid[r_mu][col_idx] = "*"

    lines: list[str] = []
    for r in range(height):
        y_val = y_max - (r / (height - 1)) * (y_max - y_min)
        row_str = "".join(grid[r])
        tag = "FLR" if r == floor_row else ("0.0" if r == zero_row else "   ")
        lines.append(f" {y_val:+5.2f} {tag} |{row_str}|")
    return lines


def format_status_readout(ledger: Ledger) -> str:
    """Render an 80-column plain-ASCII engineering readout for `thermostat status`."""
    m = compute_odometer_metrics(ledger)

    if m["probe_catch_rate"] is not None:
        probe_str = f"{m['probe_caught']}/{m['probe_total']} ({m['probe_catch_rate'] * 100.0:5.1f}%)"
    else:
        probe_str = "0/0 (N/A - no fault probes completed)"

    if m["median_skeleton_ttg_sec"] is not None:
        ttg_str = f"{m['median_skeleton_ttg_sec']:.2f}s"
    else:
        ttg_str = "N/A"

    mu = m["skill_mean"]
    sd = m["skill_std"]
    q10 = m["skill_q10"]
    margin = q10 - m["floor_hat"]
    chain_short = m["chain_head_hash"][:16]
    db_disp = m["db_path"]
    if len(db_disp) > 53:
        db_disp = "..." + db_disp[-50:]

    traj_lines = _render_15_line_trajectory(m["posteriors"], floor_hat=m["floor_hat"], width=64)

    def _box_line(inner: str) -> str:
        return f"| {inner:<76} |"[:80]

    lines = [
        "+" + "-" * 78 + "+",
        _box_line("SKILL THERMOSTAT :: LOCAL TELEMETRY ODOMETER (MILESTONE 1)"),
        "+" + "-" * 78 + "+",
        _box_line(f"Ledger DB            : {db_disp}"),
        _box_line(
            f"Total Interventions  : {m['total_interventions']:<18d} Observed Runs : {m['total_events']}"
        ),
        _box_line(f"Probe Catch Rate     : {probe_str}"),
        _box_line(f"Median Skeleton TTG  : {ttg_str}"),
        _box_line(
            f"Posterior Skill      : mu = {mu:+.3f} +/- {sd:.3f} (q10 = {q10:+.3f}, m = {margin:+.3f})"
        ),
        _box_line(
            f"Thermostat State     : {m['controller_level']:<26} Alpha Gain    : {m['alpha']:.2f}"
        ),
        _box_line(
            f"Chain Head (SHA-256) : {chain_short}... (verified={str(m['chain_valid'])})"
        ),
        "+" + "-" * 78 + "+",
        _box_line("POSTERIOR SKILL TRAJECTORY (15-LINE ASCII: '*'=mean, 'v'=q10, '-'=floor)"),
        "+" + "-" * 78 + "+",
    ]
    for tl in traj_lines:
        padded = f"|{tl:<78}|"
        lines.append(padded[:80])
    lines.append("+" + "-" * 78 + "+")
    return "\n".join(lines)


def generate_proof_receipt(ledger: Ledger, signing_key: str | None = None) -> dict[str, Any]:
    """Generate a signed JSON receipt containing only the aggregate posterior verdict and SHA-256 hash chain."""
    m = compute_odometer_metrics(ledger)
    margin = m["skill_q10"] - m["floor_hat"]
    certified = bool(m["total_events"] >= 1 and margin >= -0.05)

    verdict_label = "CERTIFIED_UNASSISTED_COMPETENCE" if certified else "BELOW_COMPETENCE_THRESHOLD"

    payload: dict[str, Any] = {
        "schema_version": "skill-thermostat-proof/v1",
        "issued_at": int(time.time()),
        "verdict": {
            "status": verdict_label,
            "certified": certified,
            "skill_mean": round(m["skill_mean"], 4),
            "skill_std": round(m["skill_std"], 4),
            "skill_q10": round(m["skill_q10"], 4),
            "floor_threshold": round(m["floor_hat"], 4),
            "safety_margin_q10": round(margin, 4),
            "controller_level": m["controller_level"],
            "total_observed_events": m["total_events"],
            "probe_catch_rate": (
                round(m["probe_catch_rate"], 4) if m["probe_catch_rate"] is not None else None
            ),
        },
        "hash_chain": {
            "algorithm": "SHA-256",
            "genesis_hash": GENESIS_HASH,
            "chain_head_hash": m["chain_head_hash"],
            "length": len(m["event_hashes"]),
            "event_hashes": m["event_hashes"],
        },
    }

    secret = (
        signing_key
        or os.environ.get("THERMOSTAT_SIGNING_KEY")
        or f"local-thermostat-key-{m['chain_head_hash'][:16]}"
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    key_fingerprint = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]

    payload["signature"] = {
        "algorithm": "HMAC-SHA256",
        "key_fingerprint": key_fingerprint,
        "digest": sig,
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="thermostat",
        description="Skill Thermostat CLI: local telemetry odometer, external repo adapter, and proof exporter.",
    )
    sub = parser.add_subparsers(dest="subcommand")

    p_status = sub.add_parser("status", help="Render 80-column ASCII posterior telemetry odometer.")
    p_status.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")

    p_proof = sub.add_parser(
        "export-proof",
        help="Export signed JSON competence receipt with SHA-256 hash chain (zero raw code exposed).",
    )
    p_proof.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")
    p_proof.add_argument("--out", default=None, help="Optional file path to write JSON proof receipt")

    p_attach = sub.add_parser(
        "attach",
        help="Attach Skill Thermostat to an external Python or Go target file and test command.",
    )
    p_attach.add_argument("target_file", help="Path to Python (.py) or Go (.go) source file")
    p_attach.add_argument("--repo-path", default="", help="Optional repository root directory")
    p_attach.add_argument("--domain", default=None, help="Domain tag (e.g. go:ledger, py:parser, py:algo)")
    p_attach.add_argument("--test-cmd", default="", help="Test command to run in observer")
    p_attach.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")

    p_inject = sub.add_parser(
        "inject",
        help="Snapshot clean file hash, apply AST/Go transformation in-place on disk, and log open intervention.",
    )
    p_inject.add_argument("--target", required=True, help="Target .py or .go file path")
    p_inject.add_argument(
        "--mode",
        default="auto",
        help="Intervention mode: auto | skeleton | probe | full (or LEVEL_SKELETON | LEVEL_PROBE_FAULT | LEVEL_FULL)",
    )
    p_inject.add_argument("--domain", default=None, help="Domain tag (e.g. go:ledger, py:parser, py:algo)")
    p_inject.add_argument("--function", default=None, help="Optional target function name")
    p_inject.add_argument("--seed", type=int, default=0, help="Deterministic mutation seed")
    p_inject.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")

    p_restore = sub.add_parser(
        "restore",
        help="Restore a target file from its clean snapshot in .thermostat.db.",
    )
    p_restore.add_argument("--target", required=True, help="Target .py or .go file path")
    p_restore.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")

    args = parser.parse_args(argv)
    cmd = args.subcommand or "status"
    db_path = getattr(args, "db", None)
    ledger = Ledger(db_path=db_path)

    if cmd == "status":
        print(format_status_readout(ledger))
        return 0

    if cmd == "export-proof":
        receipt = generate_proof_receipt(ledger)
        formatted = json.dumps(receipt, indent=2)
        out_path = getattr(args, "out", None)
        if out_path:
            Path(out_path).write_text(formatted + "\n", encoding="utf-8")
        print(formatted)
        return 0

    if cmd == "attach":
        target = str(args.target_file)
        lang = detect_language("", file_path=target)
        dom = args.domain or ("go:ledger" if lang == "go" else "py:algo")
        attached = ledger.set_attachment(
            target_file=target,
            repo_path=args.repo_path,
            domain=dom,
            test_cmd=args.test_cmd,
        )
        print(
            f"[thermostat attach] target={attached['target_file']} | domain={attached['domain']} | "
            f"repo_path={attached['repo_path']} | test_cmd={attached['test_cmd'] or 'default'}"
        )
        return 0

    if cmd == "inject":
        res = inject_on_disk_intervention(
            mode=args.mode,
            ledger=ledger,
            target_path=args.target,
            seed=args.seed,
            target_function=args.function,
            domain=args.domain,
        )
        int_row = res["intervention"]
        meta = res["fault_metadata"]
        print(
            f"[thermostat inject] id={int_row['id']} | domain={res['domain']} | lang={res['language']} | "
            f"mode={res['mode']} | clean_sha256={res['clean_hash']} | mutated_sha256={int_row['code_hash']} | "
            f"{meta.get('description', '')}"
        )
        return 0

    if cmd == "restore":
        restored_path = restore_reference_target(args.target, ledger=ledger)
        print(f"[thermostat restore] restored clean snapshot -> {restored_path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

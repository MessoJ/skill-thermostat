"""Skill Thermostat — Milestone 4 External Repo Dogfooding, Multi-Domain Field Log & Console.

Serves the live engineering readout on 0.0.0.0:3000 backed by `.thermostat.db`,
`skill_thermostat/workspace.py`, `skill_thermostat/ledger.py`,
`skill_thermostat/friction.py`, `skill_thermostat/observer.py`,
`skill_thermostat/proxy.py`, `skill_thermostat/cli.py`,
`tools/audit_core.py`, `tools/stress_failures.py`,
`tools/export_field_log.py`, and `tools/export_loi_metrics.py`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from skill_thermostat.cli import (
    compute_odometer_metrics,
    format_status_readout,
    generate_proof_receipt,
)
from skill_thermostat.friction import (
    LEVEL_FULL,
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    VALID_MODES,
    apply_with_metadata,
)
from skill_thermostat.ledger import DEFAULT_DOMAIN, Ledger
from skill_thermostat.observer import run_observed_command
from skill_thermostat.proxy import process_chat_completion
from skill_thermostat.workspace import (
    DEFAULT_GO_TARGET_FILE,
    DEFAULT_TARGET_FILE,
    DEFAULT_TARGET_TEST,
    REFERENCE_GO_SOURCE,
    REFERENCE_TARGET_SOURCE,
    TARGET_FUNCTIONS,
    inject_on_disk_intervention,
    restore_reference_target,
)
from tools.audit_core import format_audit_table, run_audit
from tools.export_field_log import (
    ensure_multi_domain_dogfood_telemetry,
    export_field_log,
    format_field_log_report,
)
from tools.export_loi_metrics import export_loi_file
from tools.stress_failures import format_stress_report, run_all_stress_tests

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DB = REPO_ROOT / ".thermostat.db"

app = Flask(__name__)


def _get_ledger() -> Ledger:
    db_path = os.environ.get("THERMOSTAT_DB", str(DEFAULT_DB))
    return Ledger(db_path=db_path)


def _ensure_initial_telemetry(ledger: Ledger) -> None:
    """Seed `.thermostat.db` with multi-domain dogfooding telemetry if needed."""
    ensure_multi_domain_dogfood_telemetry(ledger)


@app.get("/api/health")
def api_health() -> Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    post = ledger.get_latest_posterior()
    return jsonify(
        {
            "status": "ok",
            "db_path": str(ledger.db_path),
            "controller_level": post["controller_level"],
            "skill_mean": post["skill_mean"],
            "skill_std": post["skill_std"],
            "domain": post.get("domain", DEFAULT_DOMAIN),
        }
    )


@app.get("/api/state")
def api_state() -> Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    if not DEFAULT_TARGET_FILE.exists():
        restore_reference_target(DEFAULT_TARGET_FILE)
    if not DEFAULT_GO_TARGET_FILE.exists():
        restore_reference_target(DEFAULT_GO_TARGET_FILE)

    metrics = compute_odometer_metrics(ledger)
    status_ascii = format_status_readout(ledger)
    audit_rows = run_audit()
    audit_ascii = format_audit_table(audit_rows)
    stress_data = run_all_stress_tests()
    stress_ascii = format_stress_report(stress_data)
    proof = generate_proof_receipt(ledger)
    field_log = export_field_log(db_path=ledger.db_path)
    field_log_ascii = format_field_log_report(field_log)
    loi_sections, loi_markdown = export_loi_file(db_path=ledger.db_path)
    active_int = ledger.get_active_intervention()
    current_disk_code = DEFAULT_TARGET_FILE.read_text(encoding="utf-8")
    domain_summaries = ledger.get_domain_summaries()

    jsonl_preview = "\n".join(
        json.dumps(r) for r in field_log["records"][:10]
    )

    return jsonify(
        {
            "metrics": metrics,
            "domain_summaries": domain_summaries,
            "status_ascii": status_ascii,
            "audit_rows": audit_rows,
            "audit_ascii": audit_ascii,
            "stress_data": stress_data,
            "stress_ascii": stress_ascii,
            "proof": proof,
            "field_log": field_log,
            "field_log_ascii": field_log_ascii,
            "field_log_jsonl_preview": jsonl_preview,
            "loi_sections": loi_sections,
            "loi_markdown": loi_markdown,
            "active_intervention": active_int,
            "workspace_file": str(DEFAULT_TARGET_FILE.relative_to(REPO_ROOT)),
            "workspace_code": current_disk_code,
            "reference_code": REFERENCE_TARGET_SOURCE,
            "target_functions": list(TARGET_FUNCTIONS),
        }
    )


@app.post("/api/workspace/inject")
def api_workspace_inject() -> tuple[Response, int] | Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    body = request.get_json(silent=True) or {}
    mode = str(body.get("mode", LEVEL_PROBE_FAULT))
    seed = int(body.get("seed", 1))
    target_function = body.get("target_function") or None
    domain = str(body.get("domain") or DEFAULT_DOMAIN)
    if mode not in VALID_MODES and mode.lower() not in ("auto", "skeleton", "probe", "full"):
        return jsonify({"error": f"Invalid mode {mode}"}), 400

    res = inject_on_disk_intervention(
        mode=mode,
        ledger=ledger,
        target_path=DEFAULT_TARGET_FILE,
        seed=seed,
        target_function=target_function,
        domain=domain,
    )
    return jsonify(
        {
            "ok": True,
            "mode": res["mode"],
            "domain": res["domain"],
            "target_function": res["target_function"],
            "target_file": str(DEFAULT_TARGET_FILE.relative_to(REPO_ROOT)),
            "workspace_code": res["transformed_code"],
            "fault_metadata": res["fault_metadata"],
            "intervention": res["intervention"],
        }
    )


@app.post("/api/workspace/restore")
def api_workspace_restore() -> Response:
    restore_reference_target(DEFAULT_TARGET_FILE)
    return jsonify(
        {
            "ok": True,
            "workspace_code": REFERENCE_TARGET_SOURCE,
        }
    )


@app.post("/api/observer/run")
def api_observer_run() -> Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    body = request.get_json(silent=True) or {}

    if "code" in body and body["code"] is not None:
        DEFAULT_TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_TARGET_FILE.write_text(str(body["code"]), encoding="utf-8")

    mode = body.get("mode")
    domain = body.get("domain")
    sim_elapsed = body.get("simulated_elapsed_sec")
    if sim_elapsed is not None:
        try:
            sim_elapsed = float(sim_elapsed)
        except (TypeError, ValueError):
            sim_elapsed = None

    exit_code, record, summary_line = run_observed_command(
        cmd=[sys.executable, "-m", "pytest", str(DEFAULT_TARGET_TEST)],
        db_path=ledger.db_path,
        target_file=DEFAULT_TARGET_FILE,
        override_mode=mode if mode in VALID_MODES else None,
        simulated_elapsed_sec=sim_elapsed,
        cwd=REPO_ROOT,
        domain=domain,
    )
    return jsonify(
        {
            "exit_code": exit_code,
            "record": record,
            "pytest_output": record.get("pytest_output", ""),
            "summary_line": summary_line,
            "status_ascii": format_status_readout(ledger),
            "metrics": compute_odometer_metrics(ledger),
            "domain_summaries": ledger.get_domain_summaries(),
            "proof": generate_proof_receipt(ledger),
            "active_intervention": ledger.get_active_intervention(),
            "workspace_code": DEFAULT_TARGET_FILE.read_text(encoding="utf-8"),
        }
    )


@app.post("/api/friction")
def api_friction() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    mode = str(body.get("mode", LEVEL_SKELETON))
    target = str(body.get("file", "workspace/target_algo.py"))
    seed = int(body.get("seed", 1))
    target_function = body.get("target_function") or None

    if mode not in VALID_MODES:
        return jsonify({"error": f"Invalid mode {mode}"}), 400

    allowed_files = {
        "workspace/target_algo.py": DEFAULT_TARGET_FILE,
        "workspace/target_ledger.go": DEFAULT_GO_TARGET_FILE,
        "skill_thermostat/controller.py": REPO_ROOT / "skill_thermostat" / "controller.py",
        "skill_thermostat/filters.py": REPO_ROOT / "skill_thermostat" / "filters.py",
        "skill_thermostat/model.py": REPO_ROOT / "skill_thermostat" / "model.py",
    }
    if target == "workspace/target_algo.py":
        source = REFERENCE_TARGET_SOURCE
    elif target == "workspace/target_ledger.go":
        source = REFERENCE_GO_SOURCE
    else:
        file_path = allowed_files.get(target, allowed_files["skill_thermostat/controller.py"])
        source = file_path.read_text(encoding="utf-8")

    res = apply_with_metadata(
        source,
        mode=mode,
        seed=seed,
        target_function=target_function if target == "workspace/target_algo.py" else None,
        file_path=target,
    )
    return jsonify(
        {
            "file": target,
            "mode": res.mode,
            "original_code": source,
            "transformed_code": res.code,
            "metadata": res.metadata,
        }
    )


@app.post("/v1/chat/completions")
@app.post("/api/proxy/completions")
def api_proxy_completions() -> Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    payload = request.get_json(silent=True) or {}
    header_mode = request.headers.get("X-Thermostat-Mode") or payload.get("thermostat_mode")
    req_count = len(ledger.get_interventions(limit=500))
    resp = process_chat_completion(
        payload=payload,
        ledger=ledger,
        dry_run_upstream=True,
        header_mode=header_mode,
        req_index=req_count,
    )
    return jsonify(resp)


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Skill Thermostat — Local Wire Proxy &amp; Telemetry Odometer</title>
  <meta name="description" content="Closed-loop Bayesian skill estimator, AST continuous friction wire proxy, local test-runner observer, and terminal odometer." />
  <meta property="og:title" content="Skill Thermostat — Local Wire Proxy &amp; Telemetry Odometer" />
  <meta property="og:description" content="Closed-loop Bayesian skill estimator, AST continuous friction wire proxy, local test-runner observer, and terminal odometer." />
  <meta property="og:type" content="website" />
  <style>
    :root {
      --bg-canvas: #0B0F17;
      --bg-card: #0F141C;
      --bg-elevated: #141B26;
      --border-hairline: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --text-primary: #F8FAFC;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
      --accent-blue: #3B82F6;
      --status-green: #10B981;
      --status-amber: #F59E0B;
      --status-red: #EF4444;
      --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", system-ui, sans-serif;
      --font-mono: "SF Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-canvas);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 13px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }
    .mono {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }
    header {
      border-bottom: 1px solid var(--border-hairline);
      background: var(--bg-card);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .brand-sub {
      color: var(--text-secondary);
      font-size: 12px;
    }
    .top-metrics {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }
    .metric-chip {
      display: flex;
      align-items: baseline;
      gap: 8px;
      padding: 4px 10px;
      background: var(--bg-elevated);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      font-size: 12px;
    }
    .metric-chip .lbl {
      color: var(--text-secondary);
    }
    .metric-chip .val {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      font-weight: 600;
    }
    .val-green { color: var(--status-green); }
    .val-amber { color: var(--status-amber); }
    .val-red { color: var(--status-red); }
    main {
      max-width: 1400px;
      margin: 0 auto;
      padding: 18px 24px 36px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .nav-tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border-hairline);
      padding-bottom: 12px;
      flex-wrap: wrap;
    }
    .tab-btn {
      background: var(--bg-card);
      color: var(--text-secondary);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 7px 13px;
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .tab-btn:hover {
      color: var(--text-primary);
      border-color: var(--border-strong);
    }
    .tab-btn.active {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border-color: var(--accent-blue);
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1.02fr 0.98fr;
      gap: 18px;
      align-items: start;
    }
    @media (max-width: 1120px) {
      .grid-2 { grid-template-columns: 1fr; }
    }
    .panel {
      background: var(--bg-card);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      overflow: hidden;
    }
    .panel-header {
      padding: 11px 16px;
      border-bottom: 1px solid var(--border-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .panel-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .panel-subtitle {
      font-size: 12px;
      color: var(--text-secondary);
    }
    .panel-body {
      padding: 14px 16px;
    }
    pre.terminal {
      background: #070A0F;
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.42;
      color: #E2E8F0;
      overflow-x: auto;
      white-space: pre;
    }
    textarea.code-editor {
      width: 100%;
      min-height: 270px;
      background: #070A0F;
      color: #F8FAFC;
      border: 1px solid var(--border-strong);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.45;
      resize: vertical;
      tab-size: 4;
    }
    .controls-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 10px;
    }
    select, input[type="text"] {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 6px 10px;
      font-family: var(--font-sans);
      font-size: 12px;
    }
    button.action-btn {
      background: var(--accent-blue);
      color: #FFFFFF;
      border: 1px solid var(--accent-blue);
      border-radius: 6px;
      padding: 6px 12px;
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
    }
    button.action-btn.secondary {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border-color: var(--border-strong);
    }
    button.action-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }
    .table-wrap {
      overflow-x: auto;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    table.data-table th,
    table.data-table td {
      padding: 6px 7px;
      border-bottom: 1px solid var(--border-hairline);
      text-align: left;
      white-space: nowrap;
    }
    table.data-table th {
      color: var(--text-secondary);
      font-weight: 500;
      background: var(--bg-elevated);
    }
    table.data-table td.num,
    table.data-table th.num {
      text-align: right;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }
    .hidden { display: none !important; }
    .status-banner {
      margin-bottom: 10px;
      padding: 8px 11px;
      border-radius: 6px;
      background: var(--bg-elevated);
      border: 1px solid var(--border-hairline);
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--status-green);
      white-space: pre-wrap;
    }
    .status-banner.warn {
      color: var(--status-amber);
    }
    .status-banner.bad {
      color: var(--status-red);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
      </svg>
      <div>
        <h1>Skill Thermostat</h1>
        <div class="brand-sub">Physical On-Disk AST/Go Fault Loop, Multi-Domain Hysteresis Filter &amp; Odometer</div>
      </div>
    </div>
    <div class="top-metrics">
      <div class="metric-chip">
        <span class="lbl">Posterior Skill</span>
        <span class="val" id="hdrSkill">--</span>
      </div>
      <div class="metric-chip">
        <span class="lbl">Lower Bound (q10)</span>
        <span class="val" id="hdrQ10">--</span>
      </div>
      <div class="metric-chip">
        <span class="lbl">Thermostat State</span>
        <span class="val" id="hdrMode">--</span>
      </div>
      <div class="metric-chip">
        <span class="lbl">Probe Catch Rate</span>
        <span class="val" id="hdrCatch">--</span>
      </div>
    </div>
  </header>

  <main>
    <nav class="nav-tabs" aria-label="Instrument Views">
      <button class="tab-btn active" data-tab="odometer" id="tabBtnOdometer">1. Odometer &amp; Live Repair Loop</button>
      <button class="tab-btn" data-tab="friction" id="tabBtnFriction">2. Python/Go Friction &amp; Proxy</button>
      <button class="tab-btn" data-tab="audit" id="tabBtnAudit">3. Core Math Audit (3-State Hysteresis)</button>
      <button class="tab-btn" data-tab="proof" id="tabBtnProof">4. Zero-Knowledge Proof &amp; Mozilla LOI</button>
      <button class="tab-btn" data-tab="failures" id="tabBtnFailures">5. Failure Modes (Before vs. After)</button>
      <button class="tab-btn" data-tab="fieldlog" id="tabBtnFieldLog">6. Longitudinal Field Log (Dogfood Telemetry)</button>
    </nav>

    <!-- TAB 1: TERMINAL ODOMETER & PHYSICAL REPAIR LOOP -->
    <section id="view-odometer" class="grid-2">
      <div style="display: flex; flex-direction: column; gap: 18px;">
        <div class="panel">
          <div class="panel-header">
            <div>
              <div class="panel-title">Terminal Odometer Readout (thermostat status)</div>
              <div class="panel-subtitle">Live 80-column ASCII output computed from .thermostat.db</div>
            </div>
            <span class="mono panel-subtitle" id="dbPathLabel">.thermostat.db</span>
          </div>
          <div class="panel-body">
            <pre class="terminal" id="odometerAscii">Loading telemetry odometer...</pre>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <div>
              <div class="panel-title">Recorded Telemetry Ledger (.thermostat.db :: events &amp; posteriors)</div>
              <div class="panel-subtitle">Domain-scoped posteriors, physical diffs (0.000 when unedited), and AST verification</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="num">#</th>
                    <th>Domain</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th class="num">Exit</th>
                    <th class="num">TTG (s)</th>
                    <th class="num">Diff</th>
                    <th class="num">Skill mu</th>
                    <th class="num">Skill sd</th>
                  </tr>
                </thead>
                <tbody id="ledgerTableBody"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Live Code Buffer &amp; 4-Primitive Repair Loop (workspace/target_algo.py)</div>
            <div class="panel-subtitle">Select a function, inject an AST fault, run pytest unedited (view assertion failure below), repair, and re-run</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="controls-row">
            <label for="injectMode" class="panel-subtitle">Mode:</label>
            <select id="injectMode" aria-label="Intervention Mode">
              <option value="LEVEL_PROBE_FAULT">LEVEL_PROBE_FAULT (Inject Boundary Bug)</option>
              <option value="LEVEL_SKELETON">LEVEL_SKELETON (Strip Function Bodies)</option>
              <option value="LEVEL_FULL">LEVEL_FULL (Full Reference Code)</option>
            </select>
            <label for="targetFuncSelect" class="panel-subtitle">Function:</label>
            <select id="targetFuncSelect" aria-label="Target Algorithmic Function">
              <option value="rolling_breach_rate">rolling_breach_rate</option>
              <option value="bisect_threshold">bisect_threshold</option>
              <option value="token_bucket_allow">token_bucket_allow</option>
              <option value="ewma_variance">ewma_variance</option>
            </select>
            <label for="domainSelect" class="panel-subtitle">Domain:</label>
            <select id="domainSelect" aria-label="Skill Domain Tag">
              <option value="py:algo">py:algo</option>
              <option value="go:ledger">go:ledger</option>
              <option value="py:parser">py:parser</option>
              <option value="rust:core">rust:core</option>
            </select>
          </div>
          <div class="controls-row">
            <button class="action-btn secondary" id="injectBtn">Inject Intervention</button>
            <button class="action-btn secondary" id="loadFixBtn">Apply Reference Fix in Buffer</button>
            <button class="action-btn" id="runObserverBtn">Run Observed Pytest</button>
          </div>

          <div id="activeInterventionBanner" class="status-banner warn">Target: workspace/target_algo.py | Test Suite: pytest tests/test_target_algo.py</div>
          <div id="observerBanner" class="status-banner hidden"></div>

          <label for="workspaceEditor" class="panel-subtitle" style="display:block; margin-bottom:6px;">Physical Buffer (`workspace/target_algo.py` on disk):</label>
          <textarea id="workspaceEditor" class="code-editor" spellcheck="false" autocapitalize="off" autocomplete="off"></textarea>

          <label for="pytestTracebackOutput" class="panel-subtitle" style="display:block; margin:10px 0 6px;">Live Pytest Assertion Traceback &amp; Runner Output:</label>
          <pre class="terminal" id="pytestTracebackOutput">Click "Inject Intervention" and then "Run Observed Pytest" to inspect real pytest assertion failures.</pre>
        </div>
      </div>
    </section>

    <!-- TAB 2: AST FRICTION & WIRE PROXY -->
    <section id="view-friction" class="grid-2 hidden">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Continuous Multi-Language Friction Engine (skill_thermostat.friction)</div>
            <div class="panel-subtitle">Transform Python (.py) and Go (.go) modules across LEVEL_FULL, LEVEL_SKELETON, and LEVEL_PROBE_FAULT</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="controls-row">
            <label for="frictionFile" class="panel-subtitle">Source File:</label>
            <select id="frictionFile" aria-label="Source File">
              <option value="workspace/target_algo.py">workspace/target_algo.py (Python AST)</option>
              <option value="workspace/target_ledger.go">workspace/target_ledger.go (Go Source)</option>
              <option value="skill_thermostat/controller.py">skill_thermostat/controller.py</option>
              <option value="skill_thermostat/filters.py">skill_thermostat/filters.py</option>
              <option value="skill_thermostat/model.py">skill_thermostat/model.py</option>
            </select>
            <label for="frictionMode" class="panel-subtitle">Friction Mode:</label>
            <select id="frictionMode" aria-label="Friction Mode">
              <option value="LEVEL_PROBE_FAULT">LEVEL_PROBE_FAULT</option>
              <option value="LEVEL_SKELETON">LEVEL_SKELETON</option>
              <option value="LEVEL_FULL">LEVEL_FULL</option>
            </select>
            <button class="action-btn" id="applyFrictionBtn">Transform Source</button>
          </div>
          <div id="frictionMetaBanner" class="status-banner">Select a file/mode and click Transform Source.</div>
          <pre class="terminal" id="frictionCodeOutput"></pre>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">OpenAI-Compatible Wire Proxy (/v1/chat/completions)</div>
            <div class="panel-subtitle">Intercepts editor LLM completions, applies AST/Go friction, and logs active probes</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="controls-row">
            <label for="proxyForceMode" class="panel-subtitle">Controller State:</label>
            <select id="proxyForceMode" aria-label="Proxy Controller State">
              <option value="LEVEL_FULL">LEVEL_FULL (Untouched Code)</option>
              <option value="LEVEL_SKELETON">LEVEL_SKELETON (Signatures Only)</option>
              <option value="LEVEL_PROBE_FAULT">LEVEL_PROBE_FAULT (Inject Boundary Bug)</option>
            </select>
            <button class="action-btn" id="fireProxyBtn">Send /v1/chat/completions Request</button>
          </div>
          <div id="proxyMetaBanner" class="status-banner hidden"></div>
          <pre class="terminal" id="proxyOutput">Click "Send /v1/chat/completions Request" to inspect the wire proxy response.</pre>
        </div>
      </div>
    </section>

    <!-- TAB 3: CORE MATH AUDIT -->
    <section id="view-audit" class="panel hidden">
      <div class="panel-header">
        <div>
          <div class="panel-title">Standalone Core Math &amp; 3-State Hysteresis Trace (tools/audit_core.py)</div>
          <div class="panel-subtitle">Deterministic 20-step trace cycling LEVEL_FULL -> LEVEL_SKELETON -> LEVEL_PROBE_FAULT -> LEVEL_FULL</div>
        </div>
      </div>
      <div class="panel-body">
        <pre class="terminal" id="auditAscii"></pre>
      </div>
    </section>

    <!-- TAB 4: ZERO-KNOWLEDGE PROOF RECEIPT & MOZILLA LOI DRAFT -->
    <section id="view-proof" class="grid-2 hidden">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Signed Competence Proof Receipt (thermostat export-proof)</div>
            <div class="panel-subtitle">Aggregate posterior threshold verdict and SHA-256 event hash chain with HMAC-SHA256 signature</div>
          </div>
        </div>
        <div class="panel-body">
          <pre class="terminal" id="proofJson"></pre>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Mozilla Track II LOI Draft (docs/MOZILLA_LOI_DRAFT.md)</div>
            <div class="panel-subtitle">10-field word-count-locked submission generated via tools/export_loi_metrics.py</div>
          </div>
        </div>
        <div class="panel-body">
          <pre class="terminal" id="loiMarkdown"></pre>
        </div>
      </div>
    </section>

    <!-- TAB 5: WHERE THIS MODEL BREAKS (FAILURE MODES) -->
    <section id="view-failures" class="panel hidden">
      <div class="panel-header">
        <div>
          <div class="panel-title">Where This Model Breaks — Before vs. After Mitigations (tools/stress_failures.py)</div>
          <div class="panel-subtitle">1. Domain-Scoped Posteriors vs. Naive Scalar | 2. Circadian Huber Cap vs. Naive Latency | 3. Copy-Paste Velocity Guard</div>
        </div>
      </div>
      <div class="panel-body">
        <pre class="terminal" id="stressAscii"></pre>
      </div>
    </section>

    <!-- TAB 6: LONGITUDINAL FIELD LOG (DOGFOOD TELEMETRY) -->
    <section id="view-fieldlog" class="grid-2 hidden">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Longitudinal Field Log Summary (tools/export_field_log.py)</div>
            <div class="panel-subtitle">Grouped by domain (py:algo, go:ledger, py:parser) with p50/p90 TTG, probe catch rates, and anomaly counters</div>
          </div>
        </div>
        <div class="panel-body">
          <pre class="terminal" id="fieldLogAscii"></pre>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Sanitized Hash-Chained JSONL Export (data/dogfood_telemetry_v1.jsonl)</div>
            <div class="panel-subtitle">Cryptographically verified SHA-256 chain (file paths hashed to path_sha256:...)</div>
          </div>
        </div>
        <div class="panel-body">
          <pre class="terminal" id="fieldLogJsonl"></pre>
        </div>
      </div>
    </section>
  </main>

  <script>
    "use strict";
    const $ = (id) => document.getElementById(id);
    let referenceSourceCache = "";

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const target = btn.getAttribute("data-tab");
        ["odometer", "friction", "audit", "proof", "failures", "fieldlog"].forEach((t) => {
          $("view-" + t).classList.toggle("hidden", t !== target);
        });
      });
    });

    function renderState(data, preserveEditor) {
      const m = data.metrics;
      if (data.reference_code) {
        referenceSourceCache = data.reference_code;
      }
      if (!preserveEditor && data.workspace_code !== undefined) {
        $("workspaceEditor").value = data.workspace_code;
      }

      $("hdrSkill").textContent = (m.skill_mean >= 0 ? "+" : "") + m.skill_mean.toFixed(3) + " +/- " + m.skill_std.toFixed(3);
      $("hdrSkill").className = "val " + (m.skill_mean >= 0 ? "val-green" : "val-amber");

      $("hdrQ10").textContent = (m.skill_q10 >= 0 ? "+" : "") + m.skill_q10.toFixed(3);
      $("hdrQ10").className = "val " + (m.skill_q10 >= m.floor_hat ? "val-green" : "val-red");

      $("hdrMode").textContent = m.controller_level;
      $("hdrMode").className = "val " + (
        m.controller_level === "LEVEL_FULL" ? "val-green" :
        m.controller_level === "LEVEL_SKELETON" ? "val-amber" : "val-red"
      );

      if (m.probe_catch_rate !== null && m.probe_catch_rate !== undefined) {
        $("hdrCatch").textContent = m.probe_caught + "/" + m.probe_total + " (" + (m.probe_catch_rate * 100).toFixed(0) + "%)";
      } else {
        $("hdrCatch").textContent = "0/0";
      }

      $("dbPathLabel").textContent = m.db_path;
      $("odometerAscii").textContent = data.status_ascii;
      if (data.audit_ascii) $("auditAscii").textContent = data.audit_ascii;
      if (data.stress_ascii) $("stressAscii").textContent = data.stress_ascii;
      if (data.proof) $("proofJson").textContent = JSON.stringify(data.proof, null, 2);
      if (data.loi_markdown) $("loiMarkdown").textContent = data.loi_markdown;
      if (data.field_log_ascii) $("fieldLogAscii").textContent = data.field_log_ascii;
      if (data.field_log_jsonl_preview) $("fieldLogJsonl").textContent = data.field_log_jsonl_preview;

      const act = data.active_intervention;
      const actBanner = $("activeInterventionBanner");
      if (act) {
        const desc = (act.fault_metadata && act.fault_metadata.description) || act.intervention_mode;
        const fnTag = act.target_function ? (" fn=" + act.target_function + " |") : "";
        actBanner.textContent = "OPEN INTERVENTION #" + act.id + " [" + act.intervention_mode + "]" + fnTag + " sha256=" + act.code_hash + " | " + desc;
        actBanner.className = "status-banner warn";
      } else {
        actBanner.textContent = "Workspace clean (no unresolved intervention). Select a function and click 'Inject Intervention' to mutate workspace/target_algo.py on disk.";
        actBanner.className = "status-banner";
      }

      const tbody = $("ledgerTableBody");
      tbody.innerHTML = "";
      const events = m.events || [];
      const posts = m.posteriors || [];
      for (let i = events.length - 1; i >= 0; i--) {
        const ev = events[i];
        const po = posts[i] || {};
        const tr = document.createElement("tr");
        const mu = po.skill_mean !== undefined ? ((po.skill_mean >= 0 ? "+" : "") + po.skill_mean.toFixed(3)) : "--";
        const sd = po.skill_std !== undefined ? po.skill_std.toFixed(3) : "--";
        const modeShort = String(ev.intervention_mode || "").replace("LEVEL_", "");
        const vStatus = ev.verification_status || (ev.test_exit_code === 0 ? "VERIFIED_PASS" : "FAILED");
        const domTag = ev.domain || "py:algo";
        tr.innerHTML =
          '<td class="num">' + ev.id + '</td>' +
          '<td class="mono">' + domTag + '</td>' +
          '<td class="mono">' + modeShort + '</td>' +
          '<td class="mono">' + vStatus + '</td>' +
          '<td class="num">' + ev.test_exit_code + '</td>' +
          '<td class="num">' + Number(ev.time_to_green_sec).toFixed(2) + '</td>' +
          '<td class="num">' + Number(ev.edit_distance_ratio).toFixed(3) + '</td>' +
          '<td class="num">' + mu + '</td>' +
          '<td class="num">' + sd + '</td>';
        tbody.appendChild(tr);
      }
    }

    async function loadState(preserveEditor) {
      const r = await fetch("/api/state");
      const data = await r.json();
      renderState(data, Boolean(preserveEditor));
    }

    $("injectBtn").addEventListener("click", async () => {
      const mode = $("injectMode").value;
      const target_function = $("targetFuncSelect").value;
      const domain = $("domainSelect").value;
      $("injectBtn").disabled = true;
      try {
        const r = await fetch("/api/workspace/inject", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({mode, seed: 1, target_function, domain})
        });
        const data = await r.json();
        $("workspaceEditor").value = data.workspace_code;
        $("observerBanner").classList.add("hidden");
        $("pytestTracebackOutput").textContent =
          "Injected " + mode + " into " + target_function + " (" + domain + "). Click 'Run Observed Pytest' to execute pytest against the mutated file.";
        await loadState(true);
      } finally {
        $("injectBtn").disabled = false;
      }
    });

    $("loadFixBtn").addEventListener("click", () => {
      if (referenceSourceCache) {
        $("workspaceEditor").value = referenceSourceCache;
      }
    });

    $("runObserverBtn").addEventListener("click", async () => {
      const btn = $("runObserverBtn");
      btn.disabled = true;
      btn.textContent = "Running pytest...";
      try {
        const code = $("workspaceEditor").value;
        const domain = $("domainSelect").value;
        const r = await fetch("/api/observer/run", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({code, domain})
        });
        const data = await r.json();
        const banner = $("observerBanner");
        banner.classList.remove("hidden");
        banner.className = "status-banner " + (data.exit_code === 0 ? "" : "bad");
        banner.textContent = data.summary_line;
        if (data.pytest_output) {
          $("pytestTracebackOutput").textContent = data.pytest_output;
        }
        await loadState(true);
      } finally {
        btn.disabled = false;
        btn.textContent = "Run Observed Pytest";
      }
    });

    async function runFrictionPreview() {
      const file = $("frictionFile").value;
      const mode = $("frictionMode").value;
      const target_function = $("targetFuncSelect").value;
      const r = await fetch("/api/friction", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file, mode, seed: 1, target_function})
      });
      const data = await r.json();
      $("frictionMetaBanner").textContent = "[" + data.mode + "] " + (data.metadata.description || "");
      $("frictionCodeOutput").textContent = data.transformed_code;
    }

    $("applyFrictionBtn").addEventListener("click", runFrictionPreview);

    $("fireProxyBtn").addEventListener("click", async () => {
      const btn = $("fireProxyBtn");
      btn.disabled = true;
      try {
        const mode = $("proxyForceMode").value;
        const r = await fetch("/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Thermostat-Mode": mode
          },
          body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: [{role: "user", content: "Implement bisect_threshold and rolling_breach_rate"}]
          })
        });
        const data = await r.json();
        const meta = data.x_thermostat || {};
        const banner = $("proxyMetaBanner");
        banner.classList.remove("hidden");
        banner.textContent =
          "intervention_id=" + meta.intervention_id +
          " | mode=" + meta.mode +
          " | code_hash=" + meta.code_hash +
          " | " + ((meta.fault_metadata && meta.fault_metadata.description) || "");
        $("proxyOutput").textContent = data.choices[0].message.content;
        await loadState(true);
      } finally {
        btn.disabled = false;
      }
    });

    loadState(false);
    runFrictionPreview();
  </script>
</body>
</html>
"""


@app.get("/")
def index() -> Response:
    ledger = _get_ledger()
    _ensure_initial_telemetry(ledger)
    return Response(INDEX_HTML, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

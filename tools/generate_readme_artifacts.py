#!/usr/bin/env python3
"""Generate Bell Labs / RFC-Style Technical Memo README.md (Milestone 4).

Executes `thermostat status`, `tools/audit_core.py`, `skill_thermostat.friction`,
`tools/stress_failures.py`, `tools/export_field_log.py`, and
`tools/export_loi_metrics.py`, capturing their exact 80-column ASCII outputs
and writing `README.md` with zero emojis, zero badges, and zero marketing prose.
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skill_thermostat.cli import format_status_readout
from skill_thermostat.friction import (
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    apply_with_metadata,
)
from skill_thermostat.ledger import Ledger
from skill_thermostat.workspace import REFERENCE_GO_SOURCE, REFERENCE_TARGET_SOURCE
from tools.audit_core import format_audit_table, run_audit
from tools.export_field_log import export_field_log, format_field_log_report
from tools.export_loi_metrics import export_loi_file
from tools.stress_failures import format_stress_report, run_all_stress_tests


def _build_ast_diff_artifact() -> str:
    fault_res = apply_with_metadata(
        REFERENCE_TARGET_SOURCE,
        mode=LEVEL_PROBE_FAULT,
        seed=1,
        target_function="rolling_breach_rate",
    )
    diff_lines = list(
        difflib.unified_diff(
            REFERENCE_TARGET_SOURCE.splitlines(),
            fault_res.code.splitlines(),
            fromfile="a/workspace/target_algo.py (REFERENCE)",
            tofile="b/workspace/target_algo.py (LEVEL_PROBE_FAULT: rolling_breach_rate)",
            lineterm="",
            n=2,
        )
    )
    go_fault_res = apply_with_metadata(
        REFERENCE_GO_SOURCE,
        mode=LEVEL_PROBE_FAULT,
        seed=0,
        target_function="VerifyChainWindow",
        language="go",
    )
    go_diff_lines = list(
        difflib.unified_diff(
            REFERENCE_GO_SOURCE.splitlines(),
            go_fault_res.code.splitlines(),
            fromfile="a/workspace/target_ledger.go (REFERENCE)",
            tofile="b/workspace/target_ledger.go (LEVEL_PROBE_FAULT: VerifyChainWindow)",
            lineterm="",
            n=2,
        )
    )
    skel_res = apply_with_metadata(REFERENCE_TARGET_SOURCE, mode=LEVEL_SKELETON)
    return (
        f"Python AST Metadata: {fault_res.metadata['description']}\n\n"
        + "\n".join(diff_lines)
        + f"\n\nGo Source Metadata: {go_fault_res.metadata['description']}\n\n"
        + "\n".join(go_diff_lines)
        + "\n\n--- LEVEL_SKELETON AST OUTPUT ---\n"
        + skel_res.code.strip()
    )


def generate_readme(db_path: str | Path | None = None) -> str:
    ledger = Ledger(db_path=db_path or (REPO_ROOT / ".thermostat.db"))
    field_summary = export_field_log(db_path=ledger.db_path)
    field_block = format_field_log_report(field_summary)
    status_block = format_status_readout(ledger)
    audit_block = format_audit_table(run_audit())
    stress_block = format_stress_report(run_all_stress_tests())
    ast_diff_block = _build_ast_diff_artifact()
    export_loi_file(db_path=ledger.db_path)

    readme_text = f"""# SKILL-THERMOSTAT(1) — Technical Specification & Empirical Telemetry Memo

```text
DOCUMENT:     RFC-THERMOSTAT-M4
SUBSYSTEM:    skill_thermostat (v0.4.0)
INTERFACE:    127.0.0.1:8787/v1/chat/completions | thermostat attach / inject / status
STORAGE:      .thermostat.db (SQLite3 WAL/ACID local ledger) | data/dogfood_telemetry_v1.jsonl
LOI PACKAGE:  docs/MOZILLA_LOI_DRAFT.md (10-field word-count-locked Mozilla Track II LOI)
```

---

## 1. Problem Statement & System Architecture

Unconditional AI code generation induces skill atrophy when developers offload implementation and boundary verification to an LLM. Conversely, static AI bans forfeit throughput on routine work and fail to account for individual competence margins.

`skill-thermostat` is a closed-loop control system embedded in the local Unix development loop. It intercepts OpenAI-compatible chat completion requests on `127.0.0.1:8787` (or attaches directly to external Python and Go repositories via `thermostat attach` and `thermostat inject`), transforms Python ASTs and Go source blocks according to the 10th-percentile lower confidence bound ($q_{{10}}$) of the developer's domain-scoped latent skill posterior, writes the mutated or stripped target module to disk, and observes real test runs (`time_to_green_sec`, character/AST edit distance, and exit status) to update the posterior in `.thermostat.db`.

```text
+-------------------+     POST /v1/chat/completions     +--------------------------+
| Editor / CLI      | --------------------------------> | skill_thermostat.proxy   |
| (Zed/VSCode/curl) | <-------------------------------- | + friction.py (Py / Go)  |
+-------------------+   LEVEL_FULL | SKELETON | FAULT   +------------+-------------+
                                                                     |
                                         writes physical mutation    | logs open intervention
                                         to target .py / .go file    v (SHA-256 + AST node)
+-------------------+     wraps real test suite         +--------------------------+
| Developer Edits   | --------------------------------> | skill_thermostat.observer|
| Working Tree      |     verifies AST fix + latency    | + ledger.py (.thermostat)|
+-------------------+                                   +--------------------------+
```

---

## 2. State-Space Model, Hysteresis & Failure Mitigations (`model.py`, `filters.py`, `controller.py`)

### 2.1 Domain-Scoped 2D Latent Grid & Random-Walk Drift (`SkillFilter.predict`)
For each `(language:module)` domain tag (e.g., `py:algo`, `go:ledger`, `py:parser`, `rust:core`), `.thermostat.db` maintains an independent discrete joint posterior $P_t(\\theta_i, c_j)$ over a 161-point latent skill grid $\\theta \\in [-4.0, +4.0]$ and a 5-point secret-assistance contamination grid $c \\in \\{{0.0, 0.1, 0.2, 0.3, 0.4\\}}$, coupled via a weak global hyper-prior ($\\alpha_{{\\text{{global}}}} = 0.15$). Between observations, latent skill evolves via a Gaussian transition kernel $K(\\theta' \\mid \\theta; \\mu_{{\\text{{drift}}}}, \\sigma_{{\\text{{drift}}}})$:
- **Assisted transition (`LEVEL_FULL`)**: Downward-biased, wider drift $(\\mu_{{\\text{{wide}}}} = -0.04, \\sigma_{{\\text{{wide}}}} = 0.08)$ reflecting potential skill decay under passive reliance.
- **Unassisted transition (`LEVEL_SKELETON`, `LEVEL_PROBE_FAULT`)**: Effortful practice drift $(\\mu_{{\\text{{learn}}}} = +0.015, \\sigma_q = 0.047)$.

### 2.2 Joint Probit, Log-Normal Latency & Circadian Huber Cap (`SkillFilter.update_joint`)
Each local test execution produces a joint observation tuple $z_t = (y_t, T_t, \\delta_t, m_t, v_t)$, where $y_t \\in \\{{0, 1\\}}$ is the binary test pass indicator (`test_exit_code == 0`), $T_t$ is wall-clock time-to-green (`time_to_green_sec`), $\\delta_t \\in [0, 1]$ is the normalized sequence edit distance between the served intervention and current working tree, $m_t$ is the intervention mode, and $v_t \\in \\{{0, 1\\}}$ indicates whether the target AST/Go node was physically repaired.

1. **Binary Probit Pass Probability**:
   $$P_{{\\text{{solo}}}}(y_t = 1 \\mid \\theta, d) = \\Phi\\left(a(\\theta - d)\\right), \\quad a = 1.5$$
2. **Log-Normal Time-to-Green with Circadian Huber Damping**:
   Expected log completion time decreases with skill margin $(\\theta - d)$ relative to baseline $\\tau_0 = 30.0\\text{{s}}$. To prevent late-night circadian fatigue ($T_t > 120.0\\text{{s}}$ on verified passes) from destroying an established posterior, effective latency is Huber-capped at $T_{{\\text{{cap}}}} = 120.0\\text{{s}}$ when $y_t = 1$ and $v_t = 1$ (`VERIFIED_PASS_FATIGUE_DAMPED`):
   $$\\mu_{{\\log T}}(\\theta, d) = \\ln(\\tau_0) - \\beta_{{\\text{{lat}}}}(\\theta - d), \\quad \\beta_{{\\text{{lat}}}} = 0.45, \\quad \\sigma_{{\\log T}} = 0.70$$
   $$\\ell_{{\\text{{lat}}}}(\\theta \\mid T_t, d) = \\exp\\left(-\\frac{{\\gamma_{{\\text{{lat}}}}}}{{2\\sigma_{{\\log T}}^2}}\\left(\\ln(\\operatorname{{clip}}(T_t, 3, T_{{\\text{{cap}}}}) - \\mu_{{\\log T}}(\\theta, d)\\right)^2\\right), \\quad \\gamma_{{\\text{{lat}}}} = 0.42$$
3. **AST Repair & Velocity Integrity Gates**:
   - `UNVERIFIED_PASS`: If $y_t = 1$ under `LEVEL_PROBE_FAULT` or `LEVEL_SKELETON` but $\\delta_t = 0$ or $v_t = 0$, likelihood is set flat ($\\ell(\\theta) = 1$), yielding zero positive skill update.
   - `ANOMALY_PASTE_SUSPECTED`: If unassisted edit velocity exceeds human typing/reading bounds ($\\text{{chars/sec}} > 25.0$ or $T_t < 3.0\\text{{s}}$ with $\\delta_t \\ge 0.15$), positive skill update is blocked and posterior mass shifts toward higher contamination $c$.

### 2.3 3-Tier Hysteresis Controller (`Thermostat.decide_hysteresis`)
Using the posterior 10th percentile $q_{{10,t}}$ and cadence $K = 5$:
- `LEVEL_FULL` when $q_{{10,t}} \\ge +0.25$ (fires a scheduled `LEVEL_PROBE_FAULT` every $K$-th assisted task to verify retention).
- `LEVEL_SKELETON` when $-0.35 \\le q_{{10,t}} < +0.25$ (moderate AST signature scaffolding).
- `LEVEL_PROBE_FAULT` when $q_{{10,t}} < -0.35$ (diagnostic lock requiring unassisted boundary verification).

---

## 3. Live Terminal Odometer (`thermostat status`)

```text
{status_block}
```

---

## 4. Multi-Language Friction & Fault-Injection Diffs (`skill_thermostat/friction.py`)

```text
{ast_diff_block}
```

---

## 5. Core Math & 3-State Hysteresis Audit (`python tools/audit_core.py`)

```text
{audit_block}
```

---

## 6. Documented Model Failure Modes: Before vs. After (`python tools/stress_failures.py`)

```text
{stress_block}
```

---

## 7. Longitudinal Field Log & Dogfood Telemetry (`python tools/export_field_log.py`)

```text
{field_block}
```

---

## 8. Reproducible Verification Commands

```bash
# 1. Run full unit, multi-language friction, and physical workspace suite
pytest

# 2. Attach & inject cognitive friction into external Python or Go files
thermostat attach workspace/target_ledger.go --domain go:ledger --test-cmd "pytest"
thermostat inject --target workspace/target_ledger.go --mode probe --domain go:ledger
thermostat restore --target workspace/target_ledger.go

# 3. Export multi-domain dogfood JSONL & verify SHA-256 hash chain
python tools/export_field_log.py

# 4. Run 20-step deterministic 3-state hysteresis & latency audit
python tools/audit_core.py

# 5. Run empirical Before vs. After failure-mode stress suite
python tools/stress_failures.py

# 6. Export 10-field word-count-locked Mozilla Track II LOI draft
python tools/export_loi_metrics.py
```
"""
    (REPO_ROOT / "README.md").write_text(readme_text, encoding="utf-8")
    return readme_text


def main() -> None:
    generate_readme()
    print("[generate_readme_artifacts] wrote RFC-style README.md, data/dogfood_telemetry_v1.jsonl, and docs/MOZILLA_LOI_DRAFT.md.")


if __name__ == "__main__":
    main()

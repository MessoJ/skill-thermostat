# SKILL-THERMOSTAT(1) — Technical Specification & Empirical Telemetry Memo

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

`skill-thermostat` is a closed-loop control system embedded in the local Unix development loop. It intercepts OpenAI-compatible chat completion requests on `127.0.0.1:8787` (or attaches directly to external Python and Go repositories via `thermostat attach` and `thermostat inject`), transforms Python ASTs and Go source blocks according to the 10th-percentile lower confidence bound ($q_{10}$) of the developer's domain-scoped latent skill posterior, writes the mutated or stripped target module to disk, and observes real test runs (`time_to_green_sec`, character/AST edit distance, and exit status) to update the posterior in `.thermostat.db`.

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
For each `(language:module)` domain tag (e.g., `py:algo`, `go:ledger`, `py:parser`, `rust:core`), `.thermostat.db` maintains an independent discrete joint posterior $P_t(\theta_i, c_j)$ over a 161-point latent skill grid $\theta \in [-4.0, +4.0]$ and a 5-point secret-assistance contamination grid $c \in \{0.0, 0.1, 0.2, 0.3, 0.4\}$, coupled via a weak global hyper-prior ($\alpha_{\text{global}} = 0.15$). Between observations, latent skill evolves via a Gaussian transition kernel $K(\theta' \mid \theta; \mu_{\text{drift}}, \sigma_{\text{drift}})$:
- **Assisted transition (`LEVEL_FULL`)**: Downward-biased, wider drift $(\mu_{\text{wide}} = -0.04, \sigma_{\text{wide}} = 0.08)$ reflecting potential skill decay under passive reliance.
- **Unassisted transition (`LEVEL_SKELETON`, `LEVEL_PROBE_FAULT`)**: Effortful practice drift $(\mu_{\text{learn}} = +0.015, \sigma_q = 0.047)$.

### 2.2 Joint Probit, Log-Normal Latency & Circadian Huber Cap (`SkillFilter.update_joint`)
Each local test execution produces a joint observation tuple $z_t = (y_t, T_t, \delta_t, m_t, v_t)$, where $y_t \in \{0, 1\}$ is the binary test pass indicator (`test_exit_code == 0`), $T_t$ is wall-clock time-to-green (`time_to_green_sec`), $\delta_t \in [0, 1]$ is the normalized sequence edit distance between the served intervention and current working tree, $m_t$ is the intervention mode, and $v_t \in \{0, 1\}$ indicates whether the target AST/Go node was physically repaired.

1. **Binary Probit Pass Probability**:
   $$P_{\text{solo}}(y_t = 1 \mid \theta, d) = \Phi\left(a(\theta - d)\right), \quad a = 1.5$$
2. **Log-Normal Time-to-Green with Circadian Huber Damping**:
   Expected log completion time decreases with skill margin $(\theta - d)$ relative to baseline $\tau_0 = 30.0\text{s}$. To prevent late-night circadian fatigue ($T_t > 120.0\text{s}$ on verified passes) from destroying an established posterior, effective latency is Huber-capped at $T_{\text{cap}} = 120.0\text{s}$ when $y_t = 1$ and $v_t = 1$ (`VERIFIED_PASS_FATIGUE_DAMPED`):
   $$\mu_{\log T}(\theta, d) = \ln(\tau_0) - \beta_{\text{lat}}(\theta - d), \quad \beta_{\text{lat}} = 0.45, \quad \sigma_{\log T} = 0.70$$
   $$\ell_{\text{lat}}(\theta \mid T_t, d) = \exp\left(-\frac{\gamma_{\text{lat}}}{2\sigma_{\log T}^2}\left(\ln(\operatorname{clip}(T_t, 3, T_{\text{cap}}) - \mu_{\log T}(\theta, d)\right)^2\right), \quad \gamma_{\text{lat}} = 0.42$$
3. **AST Repair & Velocity Integrity Gates**:
   - `UNVERIFIED_PASS`: If $y_t = 1$ under `LEVEL_PROBE_FAULT` or `LEVEL_SKELETON` but $\delta_t = 0$ or $v_t = 0$, likelihood is set flat ($\ell(\theta) = 1$), yielding zero positive skill update.
   - `ANOMALY_PASTE_SUSPECTED`: If unassisted edit velocity exceeds human typing/reading bounds ($\text{chars/sec} > 25.0$ or $T_t < 3.0\text{s}$ with $\delta_t \ge 0.15$), positive skill update is blocked and posterior mass shifts toward higher contamination $c$.

### 2.3 3-Tier Hysteresis Controller (`Thermostat.decide_hysteresis`)
Using the posterior 10th percentile $q_{10,t}$ and cadence $K = 5$:
- `LEVEL_FULL` when $q_{10,t} \ge +0.25$ (fires a scheduled `LEVEL_PROBE_FAULT` every $K$-th assisted task to verify retention).
- `LEVEL_SKELETON` when $-0.35 \le q_{10,t} < +0.25$ (moderate AST signature scaffolding).
- `LEVEL_PROBE_FAULT` when $q_{10,t} < -0.35$ (diagnostic lock requiring unassisted boundary verification).

---

## 3. Live Terminal Odometer (`thermostat status`)

```text
+------------------------------------------------------------------------------+
| SKILL THERMOSTAT :: LOCAL TELEMETRY ODOMETER (MILESTONE 1)                   |
+------------------------------------------------------------------------------+
| Ledger DB            : /app/applet/.thermostat.db                            |
| Total Interventions  : 17                 Observed Runs : 15                 |
| Probe Catch Rate     : 6/9 ( 66.7%)                                          |
| Median Skeleton TTG  : 28.20s                                                |
| Posterior Skill      : mu = +1.296 +/- 0.958 (q10 = +0.081, m = +0.431)      |
| Thermostat State     : LEVEL_SKELETON             Alpha Gain    : 0.72       |
| Chain Head (SHA-256) : 9efb3e9abe1ff741... (verified=True)                   |
+------------------------------------------------------------------------------+
| POSTERIOR SKILL TRAJECTORY (15-LINE ASCII: '*'=mean, 'v'=q10, '-'=floor)     |
+------------------------------------------------------------------------------+
| +1.50     |                                                                | |
| +1.29     |              *                                                 | |
| +1.07     |              |                                                 | |
| +0.86     |              |                                                 | |
| +0.64     |     *    *   |                                                 | |
| +0.43     |    *|   *|   |                                                 | |
| +0.21     |    ||  *|| **|                                                 | |
| +0.00 0.0 |*.**|v.*|vv*||v.................................................| |
| -0.21     || ||v  ||  |||                                                  | |
| -0.43 FLR ||-||---|v--|||--------------------------------------------------| |
| -0.64     || vv   v   |||                                                  | |
| -0.86     ||          |||                                                  | |
| -1.07     ||*    *    |||                                                  | |
| -1.29     |||    |    |||                                                  | |
| -1.50     |vv    v    vvv                                                  | |
+------------------------------------------------------------------------------+
```

---

## 4. Multi-Language Friction & Fault-Injection Diffs (`skill_thermostat/friction.py`)

```text
Python AST Metadata: Line 30 in rolling_breach_rate(): flipped '<' (Lt) -> '<=' (LtE) in `x < floor`

--- a/workspace/target_algo.py (REFERENCE)
+++ b/workspace/target_algo.py (LEVEL_PROBE_FAULT: rolling_breach_rate)
@@ -8,5 +8,4 @@
 """
 from __future__ import annotations
-
 
 def bisect_threshold(values: list[float], target: float) -> int:
@@ -22,21 +21,13 @@
     return lo
 
-
-def rolling_breach_rate(scores: list[float], floor: float, window: int = 5) -> float:
+def rolling_breach_rate(scores: list[float], floor: float, window: int=5) -> float:
     """Return fraction of scores in the trailing window strictly below floor."""
     if window <= 0 or not scores:
         return 0.0
     tail = scores[-window:]
-    breaches = sum(1 for x in tail if x < floor)
+    breaches = sum((1 for x in tail if x <= floor))
     return breaches / len(tail)
 
-
-def token_bucket_allow(
-    tokens: float,
-    capacity: float,
-    refill_rate: float,
-    elapsed_sec: float,
-    cost: float = 1.0,
-) -> tuple[bool, float]:
+def token_bucket_allow(tokens: float, capacity: float, refill_rate: float, elapsed_sec: float, cost: float=1.0) -> tuple[bool, float]:
     """Refill token bucket over `elapsed_sec` and consume `cost` if available."""
     if elapsed_sec < 0.0:
@@ -44,9 +35,8 @@
     available = min(capacity, tokens + refill_rate * elapsed_sec)
     if available >= cost:
-        return True, available - cost
-    return False, available
+        return (True, available - cost)
+    return (False, available)
 
-
-def ewma_variance(samples: list[float], alpha: float = 0.25) -> float:
+def ewma_variance(samples: list[float], alpha: float=0.25) -> float:
     """Compute exponentially weighted moving variance across `samples`."""
     if len(samples) < 2:
@@ -61,12 +51,9 @@
     return var
 
-
-def clamp_assistance_gain(
-    q10: float, floor: float, m_lo: float = -0.05, m_hi: float = 0.20
-) -> float:
+def clamp_assistance_gain(q10: float, floor: float, m_lo: float=-0.05, m_hi: float=0.2) -> float:
     """Compute normalized assistance gain alpha in [0.0, 1.0]."""
     if m_hi <= m_lo:
-        raise ValueError("m_hi must exceed m_lo")
-    raw = ((q10 - floor) - m_lo) / (m_hi - m_lo)
+        raise ValueError('m_hi must exceed m_lo')
+    raw = (q10 - floor - m_lo) / (m_hi - m_lo)
     if raw < 0.0:
         return 0.0

Go Source Metadata: Line 5 in VerifyChainWindow(): flipped '<' (Lt) -> '<=' (LtE) in `if len(scores) < minCount {`

--- a/workspace/target_ledger.go (REFERENCE)
+++ b/workspace/target_ledger.go (LEVEL_PROBE_FAULT: VerifyChainWindow)
@@ -3,5 +3,5 @@
 // VerifyChainWindow checks whether trailing event digests satisfy the competence floor.
 func VerifyChainWindow(scores []float64, floor float64, minCount int) bool {
-	if len(scores) < minCount {
+	if len(scores) <= minCount {
 		return false
 	}

--- LEVEL_SKELETON AST OUTPUT ---
"""Target algorithmic module mutated on disk by Skill Thermostat interventions.

Contains 4 core algorithmic primitives cycled in the physical repair loop:
  1. `bisect_threshold`
  2. `rolling_breach_rate`
  3. `token_bucket_allow`
  4. `ewma_variance`
"""
from __future__ import annotations

def bisect_threshold(values: list[float], target: float) -> int:
    """Return the first index i where values[i] >= target, or len(values)."""
    raise NotImplementedError('complete unassisted')

def rolling_breach_rate(scores: list[float], floor: float, window: int=5) -> float:
    """Return fraction of scores in the trailing window strictly below floor."""
    raise NotImplementedError('complete unassisted')

def token_bucket_allow(tokens: float, capacity: float, refill_rate: float, elapsed_sec: float, cost: float=1.0) -> tuple[bool, float]:
    """Refill token bucket over `elapsed_sec` and consume `cost` if available."""
    raise NotImplementedError('complete unassisted')

def ewma_variance(samples: list[float], alpha: float=0.25) -> float:
    """Compute exponentially weighted moving variance across `samples`."""
    raise NotImplementedError('complete unassisted')

def clamp_assistance_gain(q10: float, floor: float, m_lo: float=-0.05, m_hi: float=0.2) -> float:
    """Compute normalized assistance gain alpha in [0.0, 1.0]."""
    raise NotImplementedError('complete unassisted')
```

---

## 5. Core Math & 3-State Hysteresis Audit (`python tools/audit_core.py`)

```text
+------------------------------------------------------------------------------+
| SKILL THERMOSTAT 3-STATE HYSTERESIS AUDIT (20 DETERMINISTIC EVENT TUPLES)    |
+------------------------------------------------------------------------------+
| STEP | TASK MODE         | OUTCOME        | POST MEAN |   Q10   | NEXT MODE  |
+------------------------------------------------------------------------------+
|    1 | LEVEL_PROBE_FAULT | PASS (  8.4s)  |   +1.3598 |  +0.533 | FULL       |
|    2 | LEVEL_SKELETON    | PASS (  9.6s)  |   +1.7210 |  +0.987 | FULL       |
|    3 | LEVEL_FULL        | PASS (  8.5s)  |   +1.6160 |  +0.871 | FULL       |
|    4 | LEVEL_FULL        | PASS (  9.1s)  |   +1.5110 |  +0.756 | FULL       |
|    5 | LEVEL_FULL        | PASS ( 10.4s)  |   +1.4060 |  +0.640 | FULL       |
|    6 | LEVEL_FULL        | PASS (  7.8s)  |   +1.3010 |  +0.525 | FULL       |
|    7 | LEVEL_FULL        | PASS ( 11.2s)  |   +1.1960 |  +0.410 | PROBE_FAULT |
|    8 | LEVEL_PROBE_FAULT | PASS (115.0s)  |   +0.9849 |  +0.281 | FULL       |
|    9 | LEVEL_FULL        | PASS ( 12.0s)  |   +0.8799 |  +0.165 | SKELETON   |
|   10 | LEVEL_FULL        | PASS ( 13.4s)  |   +0.7749 |  +0.049 | SKELETON   |
|   11 | LEVEL_SKELETON    | FAIL ( 88.0s)  |   +0.2022 |  -0.355 | PROBE_FAULT |
|   12 | LEVEL_PROBE_FAULT | FAIL (104.0s)  |   -0.0837 |  -0.577 | PROBE_FAULT |
|   13 | LEVEL_PROBE_FAULT | FAIL ( 92.5s)  |   -0.2633 |  -0.720 | PROBE_FAULT |
|   14 | LEVEL_PROBE_FAULT | FAIL (110.0s)  |   -0.4061 |  -0.838 | PROBE_FAULT |
|   15 | LEVEL_PROBE_FAULT | FAIL ( 79.4s)  |   -0.5148 |  -0.929 | PROBE_FAULT |
|   16 | LEVEL_PROBE_FAULT | PASS ( 14.2s)  |   -0.1941 |  -0.570 | PROBE_FAULT |
|   17 | LEVEL_PROBE_FAULT | PASS ( 11.8s)  |   +0.0709 |  -0.281 | SKELETON   |
|   18 | LEVEL_SKELETON    | PASS ( 10.4s)  |   +0.2936 |  -0.043 | SKELETON   |
|   19 | LEVEL_SKELETON    | PASS (  8.9s)  |   +0.4904 |  +0.165 | SKELETON   |
|   20 | LEVEL_PROBE_FAULT | PASS (  7.5s)  |   +0.6702 |  +0.354 | FULL       |
+------------------------------------------------------------------------------+
```

---

## 6. Documented Model Failure Modes: Before vs. After (`python tools/stress_failures.py`)

```text
+------------------------------------------------------------------------------+
| SKILL THERMOSTAT :: BEFORE vs AFTER FAILURE-MODE MITIGATION SUITE            |
+------------------------------------------------------------------------------+
| 1. DOMAIN-SHIFT FALSE ALARM (py:algo mastery vs 3 failures in rust:core)     |
+------------------------------------------------------------------------------+
| STEP | ACTIVE DOMAIN | OUTCOME        | BEFORE (NAIVE) | AFTER (py:algo/rust)|
+------------------------------------------------------------------------------+
|    0 | py:algo       | 8x PASS (9.5s) | mu=+2.465      | py=+2.072 rs=+0.311 |
|    1 | rust:core     | FAIL (135.0s)  | mu=+1.426      | py=+2.072 rs=-0.931 |
|    2 | rust:core     | FAIL (135.0s)  | mu=+1.079      | py=+2.072 rs=-1.192 |
|    3 | rust:core     | FAIL (135.0s)  | mu=+0.868      | py=+2.072 rs=-1.327 |
+------------------------------------------------------------------------------+
| RESULT: Failing 3 probes in rust:core leaves py:algo intact at +2.072        |
| (LEVEL_FULL) instead of collapsing to +0.868 as in the naive scalar filter. |
+------------------------------------------------------------------------------+
| 2. CIRCADIAN FATIGUE CONFOUNDING (140s-210s TTG spikes on verified passes)   |
+------------------------------------------------------------------------------+
|  # | TTG (s) | BEFORE: NAIVE (mu / q10) | AFTER: HUBER CAP (mu / q10) | FAIL |
+------------------------------------------------------------------------------+
|  1 |   140.0 | +1.885 / +1.134          | +2.283 / +1.399             | +0.669 |
|  2 |   165.0 | +1.614 / +0.969          | +2.305 / +1.424             | +0.404 |
|  3 |   190.0 | +1.419 / +0.850          | +2.325 / +1.448             | +0.232 |
|  4 |   210.0 | +1.274 / +0.758          | +2.346 / +1.471             | +0.105 |
+------------------------------------------------------------------------------+
| RESULT: Huber cap at TTG>120s preserves q10=+1.471 (vs naive q10=+0.758)   |
| when AST edits are verified (Exit=0, Diff>0), preventing false decay.        |
+------------------------------------------------------------------------------+
| 3. COPY-PASTE BYPASS (<3s external LLM paste into LEVEL_SKELETON)            |
+------------------------------------------------------------------------------+
| Input Payload        : 420 chars pasted in 1.2s (Diff=0.48)                 |
| Observed Velocity    : 350.0 chars/sec (Human Upper Bound: 25.0 chars/sec)   |
| Detector Verdict     : ANOMALY_PASTE_SUSPECTED                               |
| Before (Unguarded)   : mu = +1.6910 (FALSE INFLATION if velocity ignored)     |
| After (Velocity Cap) : mu = +0.0000 (Zero gain; c_hat: 0.200 -> 0.257)        |
+------------------------------------------------------------------------------+
```

---

## 7. Longitudinal Field Log & Dogfood Telemetry (`python tools/export_field_log.py`)

```text
+------------------------------------------------------------------------------+
| SKILL THERMOSTAT :: N=1 LONGITUDINAL FIELD LOG (MULTI-DOMAIN DOGFOODING)     |
+------------------------------------------------------------------------------+
| Export File  : data/dogfood_telemetry_v1.jsonl     Total Events : 15         |
| Chain Root   : 9efb3e9abe1ff741350e74327d51... Verified     : True       |
+------------------------------------------------------------------------------+
| DOMAIN    | TASKS | PROBE CATCH | SKEL TTG (p50/p90) | PRB TTG (p50/p90) | MU     |
+------------------------------------------------------------------------------+
| go:ledger |     5 | 2/3 ( 67%)  |  92.5s/137.3s      |  13.9s/ 15.4s     | +0.613 |
| py:algo   |     6 | 3/4 ( 75%)  |  28.2s/ 28.2s      |   9.2s/ 15.0s     | +0.670 |
| py:parser |     4 | 1/2 ( 50%)  |  11.9s/ 20.5s      |   9.6s/ 10.5s     | +1.296 |
+------------------------------------------------------------------------------+
| ANOMALY & INTEGRITY GATE COUNTERS ACROSS RECORDED SESSIONS                   |
+------------------------------------------------------------------------------+
| PROBE_FAILED_UNEDITED        : 2    | VERIFIED_PASS_FATIGUE_DAMPED : 1       |
| ANOMALY_PASTE_SUSPECTED      : 0    | UNVERIFIED_PASS              : 4       |
+------------------------------------------------------------------------------+
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

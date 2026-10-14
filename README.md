# Skill Thermostat (`skill-thermostat`)

**Skill Thermostat** is a closed-loop control system and empirical study platform that prevents AI-induced skill atrophy while preserving the productivity gains of AI coding assistance.

Instead of leaving AI assistance permanently on (which erodes unassisted competence when learners offload cognitive effort) or enforcing rigid schedules (which wastes productivity for strong, self-regulating users), the thermostat continuously estimates each user's unassisted skill from sparse, adaptive AI-off probes and steers assistance on the **10th-percentile lower confidence bound ($q_{10}$)** of their skill posterior.

---

## Core Mathematical Model (`skill_thermostat/`)

### 1. Probit Item Response & Contamination Mixture
On a task of difficulty $d \in [-2, +2]$, a worker with latent unassisted skill $\theta_t$ succeeds without assistance with probability:

$$P_{\text{solo}}(y_t = 1 \mid \theta_t, d) = \Phi\left(a(\theta_t - d)\right), \quad a = 1.5$$

When an ordinary AI-off probe is administered without strict proctoring (`trusted = False`), the worker may secretly use an external tool with unknown contamination probability $c \in \{0.0, 0.1, 0.2, 0.3, 0.4\}$. Secret assistance rescues a failed solo attempt with probability $q_{\text{AI}} = 0.70$:

$$P_{\text{obs}}(y_t = 1 \mid \theta_t, c, d) = (1 - c)\,P_{\text{solo}}(\theta_t, d) + c\left[1 - \left(1 - P_{\text{solo}}(\theta_t, d)\right)(1 - q_{\text{AI}})\right]$$

Trusted lockdown items (`trusted = True`, comprising baseline anchors and a 3% rate of practice sentinels) enforce $c = 0$, pinning $\theta_t$ and allowing the 2D Bayesian grid filter (`SkillFilter`) to jointly identify both $\theta_t$ and $c$.

### 2. Lower-Bound Assistance Control & Hazard Probe Scheduling
Given a worker's personal skill floor $\underline{\theta}$ (either $\hat{\theta}_0 - \Delta$ with $\Delta = 0.40$, or an absolute role standard $\underline{\theta}_{\text{abs}}$), the controller (`Thermostat.decide`) computes the safety margin from the sub-grid interpolated 10th percentile $q_{10,t}$:

$$m_t = q_{10,t} - \underline{\theta}, \qquad \alpha_t = \operatorname{clip}\left(\frac{m_t - m_{\text{lo}}}{m_{\text{hi}} - m_{\text{lo}}},\; 0,\; 1\right)$$

Discrete assistance tiers map $\alpha_t \in [0, 1]$ to:
* **`full`** ($\alpha_t \ge 0.67$): Complete working code and explanations allowed.
* **`hints`** ($0.34 \le \alpha_t < 0.67$): Conceptual explanations and at most 3 illustrative lines of code; AST-scrubbed against solution leaks.
* **`nudge`** ($0 < \alpha_t < 0.34$): A single Socratic question or conceptual nudge; zero code allowed.
* **`off`** ($\alpha_t = 0$ or sampled probe): Unassisted execution used to update the Bayesian filter. High-stakes/urgent tasks ($s_t > s_{\max}$) always receive `full` assistance and are never probed.

Probe probability $\pi_t \in [\pi_{\min}, \pi_{\max}]$ scales with floor-proximity risk $P(\theta_t \le \underline{\theta} + r)$, posterior standard deviation $\sigma_t$, and a staleness hazard ramp that guarantees fresh measurements before evidence expires.

---

## Repository Structure

```text
skill-thermostat/
├── skill_thermostat/          # Core Bayesian filter, controller, and toy-world simulator
│   ├── model.py               # Probit item-response functions and latent grid constants
│   ├── filters.py             # 2D Bayesian grid filter over (skill, probe contamination)
│   ├── controller.py          # Lower-bound ramp controller + hazard probe scheduler
│   ├── sim.py                 # 4-world simulator across 8 assistance policies
│   └── sweep.py               # Held-out Pareto frontier hyperparameter sweep
├── pilot/                     # Randomized human-study web platform & CAT engine
│   ├── config.py              # Validated controller parameters and study phase counts
│   ├── exercises.py           # Base item definitions and calibrated difficulty loader
│   ├── bank_ext/              # 150 validated coding exercises across pools A, B, C, P
│   ├── study.py               # SQLite study engine, CAT baseline, ZPD/Fisher task selector
│   ├── study_app.py           # Flask HTTP API and admin summary endpoints
│   ├── helper.py              # Gemini / Claude / Stub tiered tutor + AST & regex leak scrubber
│   ├── runner.py              # Local & remote isolated code execution harness
│   ├── runner_service.py      # Standalone container HTTP service for untrusted code
│   ├── calibrate.py           # Marginal Maximum Likelihood (EM + Newton-Raphson) IRT calibrator
│   ├── verdict.py             # Plain-language certification & integrity decision rules
│   ├── scenarios.py           # 10 scripted learner personas run through the real engine
│   ├── report.py              # Per-arm SQLite study database reporter
│   └── static/index.html      # Single-page coding study UI with focus telemetry
├── tools/
│   └── check_items.py         # Automated item-bank validator & AST duplicate detector
└── tests/                     # 44 pytest unit, concurrency, sandbox, and recovery tests
```

---

## Quickstart

### 1. Install & Run Tests
```bash
pip install -e ".[dev]"
pytest
```

### 2. Run Toy-World Simulations & Pareto Sweep
```bash
python -m skill_thermostat.sim --quick
python -m skill_thermostat.sweep --quick --out sweep_results.json
```

### 3. Run the Pilot Study Locally or via Hardened Docker Sandbox
```bash
# Local development server with Gemini helper (or ANTHROPIC_API_KEY, or offline StubHelper)
GEMINI_API_KEY=... python -m pilot.study_app --db study.db --port 8001

# Production two-container deployment (isolated network-free code runner)
GEMINI_API_KEY=... docker compose up --build
```

### 4. Evaluate Personas, Calibrate Items & Generate Study Reports
```bash
python -m pilot.scenarios --seeds 5
python -m pilot.calibrate study.db --out pilot/calibrated.json
python -m pilot.report study.db
```

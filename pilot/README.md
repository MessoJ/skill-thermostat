# Pilot Study Platform (`pilot/`)

The `pilot/` package implements the randomized controlled study application built on `skill_thermostat`.

## Architecture & Study Design

- **Randomized Arms (`study.py`):** Blocked randomization assigns consenting participants equally across three arms:
  1. `thermostat`: Adaptive AI assistance steered by the 10th-percentile skill lower bound ($q_{10}$) with hazard-scheduled AI-off probes and 3% lockdown sentinels.
  2. `always_on`: Full AI helper available on every practice task (no probes).
  3. `fixed_drills`: Full AI helper available except on every 5th eligible practice task, which is run AI-off.
- **62-Task Flow (`config.STUDY`):**
  1. **Adaptive Baseline (20 items from Pool A, 30 items total):** Strictly locked down (`tier = "off"`, focus telemetry active). Items are selected dynamically via **Computerized Adaptive Testing (CAT)** to maximize Posterior Expected Fisher Information at each step.
  2. **Practice Block 1 (10 items from Pool P, 96 items total):** Assisted practice tasks target the learner's Zone of Proximal Development ($\hat{\theta}_{\text{mean}} + 0.30$), whereas unassisted probes select the Pool P item that maximizes Fisher Information over the current posterior.
  3. **Mid-Study Assessment (6 items from Pool B, 12 items total):** Strictly locked down; never feeds the skill filter so it remains an independent outcome measure.
  4. **Practice Block 2 (20 items from Pool P):** Continues arm-specific assistance and probing.
  5. **Final Assessment (6 matched items from Pool C, 12 items total):** Strictly locked down; paired 1-to-1 by difficulty and structure with the learner's Pool B items.
- **Personal & Role-Based Skill Floors:**
  - For students (`floor_abs=None`), the floor is anchored at $\min(\hat{\theta}_0, d_{\max}) - \Delta$ ($\Delta = 0.40$) and capped at $q_{10,0} - 0.05$ so neither ceiling scorers nor struggling novices are locked out of initial assistance.
  - For staff (`join(consent=True, floor_abs=...)`), the floor is fixed at the role's required unassisted standard.
- **Urgent Quota:** Learners can mark up to 3 of their last 20 practice tasks `urgent`. Urgent tasks always receive `full` assistance and are never probed.
- **Tiered AI Helper & AST Scrubber (`helper.py`):** The server selects `off`, `nudge`, `hints`, or `full`. Native support for Google Gemini (`GEMINI_API_KEY`) and Anthropic Claude (`ANTHROPIC_API_KEY`), falling back to `StubHelper` offline. Outgoing LLM responses at `nudge` and `hints` are screened by `helper.scrub`, which blocks code fences exceeding line limits, raw function definitions, line-level matches, and AST-isomorphic solutions with renamed variables.

---

## Scenario Benchmark (`python -m pilot.scenarios`)

Running the 10 scripted learner personas (`--seeds 5`) through the real SQLite `Engine` yields:

```text
persona                               arm          AI share below floor end skill   verdicts
--------------------------------------------------------------------------------------------
student: strong, skill holds          thermostat        83%          0%     +1.37   keep_using_ai x5
                                      always_on        100%          0%     +1.36   not_enough_evidence x5

student: strong but AI-dependent      thermostat        54%         13%     +0.64   reduce_ai x3, use_ai_in_moderation x2
                                      always_on        100%         73%     +0.12   not_enough_evidence x5

student: weak, learns by doing        thermostat        71%          0%     +0.88   keep_using_ai x4, use_ai_in_moderation x1
                                      always_on        100%          0%     +0.31   not_enough_evidence x5

student: weak and sliding             thermostat        31%         42%     -0.31   practice_without_ai x4, reduce_ai x1
                                      always_on        100%         89%     -1.54   not_enough_evidence x5

student: gets outside help on probes  thermostat        78%         61%     -0.84   check_measurements x5
                                      always_on        100%         87%     -1.34   not_enough_evidence x5

student: erratic answers              thermostat        48%          5%     +0.55   reduce_ai x3, use_ai_in_moderation x2
                                      always_on        100%         12%     +0.32   not_enough_evidence x5

student: quits early                  thermostat        75%          0%     +1.31   not_enough_evidence x5
                                      always_on        100%          0%     +1.30   not_enough_evidence x5

staff: meets role standard            thermostat        82%          0%     +1.18   keep_using_ai x5
                                      always_on        100%          0%     +1.02   stale_evidence x5

staff: below role standard            thermostat         5%         19%     +1.45   reduce_ai x3, practice_without_ai x2
                                      always_on        100%         85%     +0.36   stale_evidence x5

staff: delivery crunch (urgent)       thermostat        77%          2%     +0.91   keep_using_ai x3, use_ai_in_moderation x2
                                      always_on        100%         18%     +0.52   stale_evidence x5
```

---

## CLI Utilities

* **Start the web server:**
  ```bash
  # Using Gemini:
  GEMINI_API_KEY=... python -m pilot.study_app --db study.db --host 127.0.0.1 --port 8001

  # Or using Anthropic Claude:
  ANTHROPIC_API_KEY=... python -m pilot.study_app --db study.db --host 127.0.0.1 --port 8001
  ```
* **Summarize study database by arm:**
  ```bash
  python -m pilot.report study.db
  ```
* **Calibrate item difficulties (MML-EM + Newton-Raphson refinement):**
  ```bash
  python -m pilot.calibrate study.db --out pilot/calibrated.json
  ```
  When `pilot/calibrated.json` is present, `pilot/exercises.py` automatically loads the empirical difficulties for all items with $n \ge 30$ unassisted responses.
* **Audit live LLM helper compliance across tiers:**
  ```bash
  GEMINI_API_KEY=... python -m pilot.live_check --n 8 --out live_check.txt
  ```
* **Validate new exercise batches:**
  ```bash
  python tools/check_items.py pilot/bank_ext/items_p4.py --existing
  ```

# Pilot app

Two engines live here, both built on the same `skill_thermostat` package.

| | Study engine (use this) | Early prototype |
|---|---|---|
| Engine | `study.py` | `engine.py` |
| Server | `study_app.py` (Flask) | `server.py` (stdlib) |
| Items | `exercises.py` + `bank_ext/`, 150 items in pools A/B/C/P | `tasks.py`, 15 items |
| Design | 3 randomized arms, baseline + mid + post assessments | single participant flow |

## Study design (study engine)

- **Arms** (blocked randomization): `thermostat`, `always_on`, `fixed_drills` (every 5th practice task AI-off).
- **Flow** (all in `config.STUDY`): 20 baseline anchors (drawn from pool A, 30 items) → 10 practice tasks (pool P, 96 items) →
  mid assessment (6 items from pool B) → 20 more practice → final assessment (the 6 matched items from pool C). 62 tasks.
  Each learner's anchors and B/C pairs come from their own seed (`Engine.plan`). B and C are 12 matched pairs; assessments never feed
  the filter, so they stay clean outcome measures.
- **Floor:** baseline mean, clipped to the anchors' difficulty range, minus 0.40. Staff can be given an absolute role standard
  instead (`join(consent, floor_abs=...)`). `config.FLOOR_RULE` switches to the more lenient "baseline lower bound" rule.
- **Helper tiers** are chosen by the server: `off` (HTTP 403 on the helper endpoint), `nudge`, `hints`, `full`. Replies
  are screened by `helper.scrub`. The model never sees reference solutions or hidden tests.
- **Urgent flag:** a learner can mark at most 3 of their last 20 practice tasks urgent. Those get full help and are never probed.
- **Activity signals:** paste, drag-drop, tab switches are logged on locked tasks. A trusted task with a suspicious signal
  loses its trusted status.
- **Keep AI or cut back?** `Engine.verdict(user)` and `summary()` give a plain-language status per person (`verdict.py`): keep_using_ai,
  keep_but_watch, use_ai_in_moderation, reduce_ai, practice_without_ai, not_enough_evidence, stale_evidence, check_measurements.
  `python -m pilot.scenarios` runs ten scripted learner types through the real engine and prints what each gets.

## Other tools

- `python -m pilot.calibrate study.db --out pilot/calibrated.json`: re-estimate item difficulties from unassisted responses (marginal ML,
  probit slope fixed at the model's 1.5, nominal difficulty as a weak prior). Recovers simulated difficulties (rmse 0.08 vs 0.50 for the
  starting guesses). If `pilot/calibrated.json` exists, the bank uses it.
- `python -m pilot.live_check` with `ANTHROPIC_API_KEY`: runs the helper at each tier on sample exercises and reports rule-breaking replies
  and replies that solve the exercise where they should not. Not yet run live.
- `python tools/check_items.py <batch.py>`: validator for new items (reference passes, empty starter fails, distinct outputs, ...).
- Sandbox: `docker compose up --build` starts the app and a separate runner container (no internet, read-only, no data). The app sends
  code to it when `RUNNER_URL` is set. Compose syntax is validated; the containers have NOT been started (no Docker daemon here).

## Run

    pip install flask numpy scipy    # anthropic only if you want the live helper
    python -m pilot.study_app --db study.db --port 8001
    python -m pilot.report study.db
    ADMIN_TOKEN=... for /api/admin/summary (header X-Admin); otherwise localhost only
    ANTHROPIC_API_KEY=... uses Claude as the helper (HELPER_MODEL overrides the model); otherwise an offline stub

## What is and isn't verified

Verified by tests (`pytest`, 40 passing): every reference solution passes and every starter and trivial wrong answer fails, 150 unique items
with matched B/C pairs and full difficulty coverage; runner (local and over HTTP, loops, errors, bad jobs, key check, fail-closed);
calibration recovery on simulated learners; arm balance, once-per-item, locked anchors and assessments, urgent never probed, assessments
do not touch the filter, suspicious activity downgrades trust, concurrent double-submit counts once, admin access; verdict bands and
integrity rules; scenario behaviour (declining learner protected, always-on users never certified, outside help with paste activity flagged,
honest fast learners not flagged, staff below standard get no AI, urgent work stays fully assisted).

Not verified / open:
- Nothing has been tried with a real person, and the Claude helper has never run against the live API.
- The 150 items were written and checked by machine. Difficulties are still nominal until `calibrate` has run on real responses (aim for
  300+ learners' worth of unassisted answers); wrong-answer coverage beyond trivial mutants has not been tested.
- The Docker sandbox has not been started. Compose and Dockerfiles are untested beyond `docker compose config`.
- The local runner is not a security sandbox. Use the remote runner for anything other people can reach.
- A second device defeats lockdown, and outside help with no pasting or tab switching is not detected by the verdict. Compare probe results
  with the locked mid and final assessments after the fact.
- Scenario personas and their learning/decay rates are my assumptions. In them the thermostat holds skill better than always-on, but with
  ~30 practice tasks per learner it rarely certifies anyone as "keep using AI" (the estimate stays too wide), and a learner who fails every
  baseline item is routed to no AI at all.
- The consent text is a placeholder. A real run needs an ethics review.
- The simulation results that chose `config.py` come from hand-built worlds, not people.

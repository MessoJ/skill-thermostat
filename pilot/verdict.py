"""Keep using AI, or cut back? A plain-language verdict from the thermostat's own evidence.

The verdict uses the same numbers the controller acts on, so what a manager or teacher reads matches what the learner experiences.

  margin = lower bound of estimated unassisted skill (10th percentile) - floor
  - floor for a student: their own baseline lower bound minus DELTA (do not slip below where you started)
  - floor for staff: an absolute standard for the role (can you do the job's core tasks without AI?)

Order of checks (first that applies wins):
  1. check_measurements   copy/paste or tab switching on many unassisted tasks: the unassisted numbers cannot be trusted, so no
                          "keep using AI" verdict is given. Two other signals were tried and removed because they flagged honest
                          fast learners as suspicious: the filter's own secret-AI estimate, and ordinary-vs-locked pass-rate gaps
                          (skill changes over time, so earlier locked tasks look harder than later ordinary ones). Outside help
                          with no copy/paste or tab switching (a second device) is NOT detected here; compare probe results with
                          the locked mid and final assessments after the fact.
  2. not_enough_evidence  fewer than MIN_MEAS unassisted measurements, a still-wide estimate, or (for a baseline-relative floor)
                          fewer than MIN_PROBES unassisted checks after practice began: right after baseline the margin is DELTA
                          by construction, which says nothing.
  2b. stale_evidence      the last unassisted check is more than STALE_AFTER practice tasks old.
  3. practice_without_ai  estimated skill is below the floor.
  4. reduce_ai            lower bound at or below the controller's low margin (m_lo): mostly unassisted work until it recovers.
  5. use_ai_in_moderation between m_lo and m_hi: hints, not full solutions.
  6. keep_but_watch       margin is high but skill has been falling.
  7. keep_using_ai        margin is high and skill is stable or rising.

The thresholds are mine, taken from the controller config and set by judgement, not validated on people.
"""
from dataclasses import asdict, dataclass

from .config import CONTROLLER

MIN_MEAS = 8          # unassisted measurements needed before any verdict
MAX_SD = 0.45         # posterior sd above which the estimate is too wide to act on
SUSPECT_FRAC = 0.25   # share of unassisted tasks with suspicious activity that voids the measurements
MIN_OBS = 4           # ordinary unassisted tasks needed before the suspicious-activity share is used
MIN_PROBES = 4        # unassisted checks after practice began (baseline-relative floors only)
STALE_AFTER = 12      # practice tasks since the last unassisted check
TREND_DROP = -0.15    # fall in estimated skill over the lookback that counts as "falling"
LOOKBACK = 8

ADVICE = {
    "keep_using_ai": "Skill is safely above the floor and stable. Keep using AI; unassisted checks continue at a low rate.",
    "keep_but_watch": "Above the floor but trending down. Keep AI for now and add scheduled unassisted practice.",
    "use_ai_in_moderation": "Close to the floor. Use AI for hints and checking, not for full solutions, and do more unassisted tasks.",
    "reduce_ai": "The lower bound is at the floor. Do mostly unassisted work until it recovers (urgent work is still fully assisted).",
    "practice_without_ai": "Estimated skill is below the floor. Unassisted practice only (urgent work excepted) until it recovers.",
    "not_enough_evidence": "Not enough unassisted measurements yet. Keep measuring; no decision about AI use.",
    "stale_evidence": "The last unassisted check is out of date, so skill may have changed. Schedule unassisted tasks before deciding.",
    "check_measurements": "Unassisted results look unreliable (copy/paste or tab switching on many tasks). Re-measure under supervision before deciding.",
}


@dataclass
class Verdict:
    status: str
    advice: str
    margin: float
    lower: float
    mean: float
    floor: float
    n_meas: int
    trend: float
    note: str = ""

    def as_dict(self):
        return asdict(self)


def decide(mean, sd, lower, floor, n_meas, trend, *, n_probes=0, since_last=0, relative_floor=True,
           probe_suspect=0.0, n_probe_obs=0, anchor_suspect=0.0, cfg=CONTROLLER):
    margin = lower - floor
    note = "improving" if (trend is not None and trend >= 0.15) else ""

    def v(status):
        return Verdict(status, ADVICE[status], float(margin), float(lower), float(mean), float(floor), int(n_meas),
                       float(trend or 0.0), note)

    if (n_probe_obs >= MIN_OBS and probe_suspect >= SUSPECT_FRAC) or anchor_suspect >= SUSPECT_FRAC:
        return v("check_measurements")
    if n_meas < MIN_MEAS or sd > MAX_SD or (relative_floor and n_probes < MIN_PROBES):
        return v("not_enough_evidence")
    if since_last > STALE_AFTER:
        return v("stale_evidence")
    if mean < floor:
        return v("practice_without_ai")
    if margin <= cfg.m_lo:
        return v("reduce_ai")
    if margin < cfg.m_hi:
        return v("use_ai_in_moderation")
    if trend is not None and trend <= TREND_DROP:
        return v("keep_but_watch")
    return v("keep_using_ai")

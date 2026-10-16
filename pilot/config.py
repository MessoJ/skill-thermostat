"""Pilot settings.

CONTROLLER is the 'robust' thermostat config that the held-out sweep validated (robust, ramp (-0.05,+0.20),
3% trusted sentinels, standard drift kernel): 0.6% of worker-time below the skill floor at a 31% productivity
cost, versus 5.1% for the best simple baseline at the same cost (3 fresh seeds, N=400, T=400). Those are
hand-built simulated worlds, not evidence about people. In the sweep each worker did 400 tasks and 30 baseline
anchors; this pilot has far fewer, so expect much wider posteriors and more probing.
"""
from skill_thermostat import ThermostatConfig

CONTROLLER = ThermostatConfig(m_lo=-0.05, m_hi=0.20, sentinel_rate=0.03)
WIDE_SHIFT, WIDE_SD = -0.04, 0.08
C_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)
DELTA = 0.40  # tolerated drop in unassisted skill below the baseline estimate
FLOOR_RULE = "mean"  # 'lower': baseline lower bound - DELTA (lenient, safe with few anchors); 'mean': baseline mean - DELTA (as simulated)

STUDY = dict(
    anchors=20,            # baseline items drawn from pool A (30); all arms; strict lockdown
    assess_n=6,            # items per assessment, drawn as matched B/C pairs from 12 pairs
    practice_total=30,     # practice tasks per learner (pool P has 96)
    assess_b_after=10,     # mid assessment (pool B) after this many practice tasks
    assess_c_after=30,     # final assessment (pool C) after this many practice tasks
    drill_every=5,         # fixed_drills arm: every 5th eligible practice task is AI-off
    urgent_max=3,          # learners may mark at most this many of their last `urgent_window` tasks urgent
    urgent_window=20,
    helper_max_per_task=30,
    practice_max_attempts=3, # maximum attempts for practice exercises before moving on
)

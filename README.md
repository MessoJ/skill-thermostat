# skill-thermostat

Research prototype. Keeps people's **unassisted** skill above a personal floor while they use an AI assistant.

1. Randomly switch the AI off on a small share of low-stakes tasks and score the solo attempt.
2. Track skill with a Bayesian filter that also estimates how often "AI-off" probes are secretly assisted
   (calibrated against rare trusted lockdown items).
3. Steer assistance on the lower confidence bound of skill: more help when safely above the floor, less near it.
   High-stakes tasks always get full assistance and are never probed.

```
pip install numpy scipy pytest
python -m pytest -q
python -m skill_thermostat.sim --quick     # smoke test
python -m skill_thermostat.sim             # full comparison (about a minute)
```

Status: simulation only. The simulated worlds are assumptions, not evidence about real people.
Nothing here has been tested on humans yet.

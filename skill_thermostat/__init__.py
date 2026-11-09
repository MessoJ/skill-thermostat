"""skill_thermostat: measure unassisted skill with randomized AI-off probes and steer AI assistance."""
import importlib

from .controller import Summary, Thermostat, ThermostatConfig
from .filters import SkillFilter
from .friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from .ledger import Ledger

__all__ = [
    "LEVEL_FULL",
    "LEVEL_PROBE_FAULT",
    "LEVEL_SKELETON",
    "Ledger",
    "SkillFilter",
    "Summary",
    "Thermostat",
    "ThermostatConfig",
    "cli",
    "friction",
    "ledger",
    "observer",
    "proxy",
    "workspace",
]
__version__ = "0.2.0"


def __getattr__(name: str):
    if name in ("cli", "friction", "ledger", "observer", "proxy", "workspace"):
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")




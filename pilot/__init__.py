"""Pilot app: coding exercises with an AI helper whose availability is steered by the skill thermostat."""
import os
from pathlib import Path


def _load_env():
    """Load key-value pairs from .env if present into os.environ."""
    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    )
    for path in candidates:
        if path.is_file():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
                break
            except Exception:
                pass


_load_env()

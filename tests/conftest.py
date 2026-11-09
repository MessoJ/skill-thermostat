from pathlib import Path
import sys
import pytest

REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    """Ensure tests run in a hermetic environment unaffected by ambient development secrets."""
    for key in ("ADMIN_TOKEN", "RUNNER_KEY", "RUNNER_URL"):
        monkeypatch.delenv(key, raising=False)


import pytest


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    """Ensure tests run in a hermetic environment unaffected by ambient development secrets."""
    for key in ("ADMIN_TOKEN", "RUNNER_KEY", "RUNNER_URL"):
        monkeypatch.delenv(key, raising=False)

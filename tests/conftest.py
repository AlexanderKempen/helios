import pytest

from helios.services import cost


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a throwaway database instead of ~/.helios."""
    monkeypatch.setenv("HELIOS_DB", str(tmp_path / "helios.db"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    cost.resolve_pricing.cache_clear()
    yield

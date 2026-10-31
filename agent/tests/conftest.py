import pytest
from fastapi.testclient import TestClient

from agent import main
from backend.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """Give every test its own seeded database and point the agent at it."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))


@pytest.fixture
def client():
    return TestClient(app)

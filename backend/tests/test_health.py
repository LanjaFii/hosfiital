from fastapi.testclient import TestClient
import os
import sys
import pytest

# Ensure project root is on sys.path for imports during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_db():
    r = client.get("/health/db")
    assert r.status_code == 200
    # database may be reachable or not depending on environment; check key presence
    assert "database" in r.json()

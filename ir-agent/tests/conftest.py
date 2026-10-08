import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("IR_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("IR_API_TOKENS", "tok-alice:alice,tok-bob:bob")
    monkeypatch.setenv("IR_RATE_LIMIT", "1000")
    from app.services import auth, ir_engine
    auth.reset_rate_limits()
    ir_engine.invalidate()
    from app.main import app
    with TestClient(app) as c:
        yield c


ALICE = {"Authorization": "Bearer tok-alice"}
BOB = {"Authorization": "Bearer tok-bob"}

import tempfile
import sqlite3
import pytest
from fastapi.testclient import TestClient

from veil.hospital_gui.main import app, init_db, _db


@pytest.fixture(scope="session")
def test_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        def _test_db():
            conn = sqlite3.connect(f.name)
            conn.row_factory = sqlite3.Row
            return conn

        monkeypatch.setattr("veil.hospital_gui.main._db", _test_db)
        init_db()
        yield


@pytest.fixture()
def client(test_db):
    return TestClient(app)

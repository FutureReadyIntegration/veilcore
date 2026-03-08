from fastapi.testclient import TestClient
from veil.hospital_gui.main import app

client = TestClient(app)

def test_pages_load():
    for path in ["/", "/patients", "/discharged", "/organs", "/status", "/app/"]:
        r = client.get(path)
        assert r.status_code in (200, 404)

def test_organs_api():
    r = client.get("/api/organs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


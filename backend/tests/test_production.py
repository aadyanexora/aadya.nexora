from fastapi.testclient import TestClient
from app.main import app
from app.core import config


def test_security_headers_and_https_redirect(monkeypatch):
    # simulate production environment
    monkeypatch.setattr(config.settings, "ENV", "PROD")
    client = TestClient(app)

    # a plain http request should be redirected to https
    r = client.get("/health", allow_redirects=False)
    assert r.status_code in (307, 308)

    # if we call with an explicit https URL we should succeed
    r2 = client.get("https://testserver/health")
    assert r2.status_code == 200

    # security headers should be present on any response
    for hdr in ["X-Frame-Options", "X-Content-Type-Options", "Strict-Transport-Security"]:
        assert hdr in r2.headers


def test_metrics_and_health(monkeypatch):
    # dev environment should not enforce https
    monkeypatch.setattr(config.settings, "ENV", "DEV")
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "app_requests_total" in r.text

    r = client.get("/health")
    data = r.json()
    assert data["status"] == "ok"
    assert "db" in data["details"]
    assert "faiss_dir_exists" in data["details"]
    # verify index size field is present (vector store loaded)
    assert "faiss_index_size" in data["details"]

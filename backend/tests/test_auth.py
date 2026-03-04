import sys
import uuid
# ensure project root is on path so "app" package can be imported when
# pytest sets cwd to tests/.
sys.path.insert(0, "/app")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_unique_email():
    return f"test+{uuid.uuid4()}@example.com"


def test_refresh_and_logout_flow():
    # register a fresh user
    email = make_unique_email()
    pwd = "password"

    r = client.post("/api/auth/register", json={"email": email, "password": pwd})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data and "refresh_token" in data
    # token should include org claim
    tok = data["access_token"]
    import jwt, os
    assert jwt.decode(tok, os.environ.get("SECRET_KEY"), algorithms=["HS256"]).get("org_id") is not None
    first_refresh = data["refresh_token"]

    # logging in should issue a new refresh token (and not revoke the previous one)
    r2 = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert r2.status_code == 200
    data2 = r2.json()
    assert "access_token" in data2 and "refresh_token" in data2
    # login token also carries org_id
    tok2 = data2["access_token"]
    assert jwt.decode(tok2, os.environ.get("SECRET_KEY"), algorithms=["HS256"]).get("org_id") is not None
    second_refresh = data2["refresh_token"]
    assert first_refresh != second_refresh

    # using the second refresh token should succeed and rotate to a third token
    r3 = client.post("/api/auth/refresh", json={"refresh_token": second_refresh})
    assert r3.status_code == 200
    data3 = r3.json()
    assert "access_token" in data3 and "refresh_token" in data3
    third_refresh = data3["refresh_token"]
    assert third_refresh != second_refresh

    # the original second token is now revoked; trying to reuse should fail
    r4 = client.post("/api/auth/refresh", json={"refresh_token": second_refresh})
    assert r4.status_code == 401

    # logout using the third token should mark it revoked
    r5 = client.post("/api/auth/logout", json={"refresh_token": third_refresh})
    assert r5.status_code == 200
    assert r5.json().get("status") == "ok"

    # trying to use the third token again for refresh should now return 401
    r6 = client.post("/api/auth/refresh", json={"refresh_token": third_refresh})
    assert r6.status_code == 401

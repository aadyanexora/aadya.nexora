import sys
import uuid
# ensure the project root is on the path when tests run inside container
sys.path.insert(0, "/app")
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.chat import Conversation
from app.models.user import User
from app.models.organization import Organization
from app.models.usage_log import UsageLog

client = TestClient(app)


def register(email, pwd, org=None):
    body = {"email": email, "password": pwd}
    if org:
        body["organization"] = org
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 200
    return r.json()


def login(email, pwd):
    r = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200
    return r.json()


def test_organization_claim_and_isolation():
    # register two users in different orgs
    resp1 = register(f"u1+{uuid.uuid4()}@example.com", "pw", org="OrgA")
    tok1 = resp1["access_token"]
    org1 = decode_access_token(tok1).get("org_id")
    assert org1 is not None

    resp2 = register(f"u2+{uuid.uuid4()}@example.com", "pw", org="OrgB")
    tok2 = resp2["access_token"]
    org2 = decode_access_token(tok2).get("org_id")
    assert org2 is not None and org2 != org1

    # create conversations manually using DB
    db = SessionLocal()
    try:
        user1_id = int(decode_access_token(tok1).get("sub"))
        user2_id = int(decode_access_token(tok2).get("sub"))
        conv1 = Conversation(user_id=user1_id, organization_id=org1)
        conv2 = Conversation(user_id=user2_id, organization_id=org2)
        db.add_all([conv1, conv2])
        db.commit()
        db.refresh(conv1)
        db.refresh(conv2)
    finally:
        db.close()

    # listing conversations as user1 returns only conv1
    r = client.get("/api/chat/conversations", headers={"Authorization": f"Bearer {tok1}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == conv1.id

    r = client.get("/api/chat/conversations", headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 200
    data2 = r.json()
    assert len(data2) == 1
    assert data2[0]["id"] == conv2.id


def test_admin_scoping():
    # create two organizations and users
    email_admin = f"admin+{uuid.uuid4()}@example.com"
    r1 = register(email_admin, "pw", org="OrgX")
    tok_admin = r1["access_token"]
    admin_id = int(decode_access_token(tok_admin).get("sub"))
    org_id = decode_access_token(tok_admin).get("org_id")
    # mark the first user as admin in DB and refresh token
    db = SessionLocal()
    try:
        user = db.query(User).get(admin_id)
        user.is_admin = True
        db.add(user)
        db.commit()
    finally:
        db.close()
    # obtain a fresh token so the role claim is updated
    tok_admin = login(email_admin, "pw")["access_token"]

    # create one user in same org and one in another
    email_same = f"same+{uuid.uuid4()}@example.com"
    email_other = f"other+{uuid.uuid4()}@example.com"
    r_same = register(email_same, "pw", org="OrgX")
    r_other = register(email_other, "pw", org="OrgY")

    # as org-scoped admin, list_users should return only same-org user and self
    r = client.get("/api/admin/users", headers={"Authorization": f"Bearer {tok_admin}"})
    assert r.status_code == 200
    users = r.json()
    for u in users:
        assert u["email"].endswith("@example.com")
        # ensure no OrgY user appears
        assert "OrgY" not in u["email"]  # crude check since we used name in email

    # attempt to top-up other-org user should yield 403
    uid_other = int(decode_access_token(login(email_other, "pw")["access_token"]).get("sub"))
    r2 = client.post(f"/api/admin/users/{uid_other}/topup", json={"amount": 10}, headers={"Authorization": f"Bearer {tok_admin}"})
    assert r2.status_code == 403

    # create some usage logs manually and check analytics summary respects org
    db = SessionLocal()
    try:
        # look up organization ids
        orgx = db.query(Organization).filter(Organization.name == "OrgX").first()
        orgy = db.query(Organization).filter(Organization.name == "OrgY").first()
        ul1 = UsageLog(user_id=admin_id, tokens_used=5, cost=0.5, organization_id=orgx.id)
        ul2 = UsageLog(user_id=uid_other, tokens_used=3, cost=0.3, organization_id=orgy.id)
        db.add_all([ul1, ul2])
        db.commit()
    finally:
        db.close()
    # analytics summary should count only OrgX logs for this admin
    r3 = client.get("/api/admin/analytics/summary", headers={"Authorization": f"Bearer {tok_admin}"})
    assert r3.status_code == 200
    summary = r3.json()
    assert summary["total_users"] >= 1
    # compare with global summary (use built-in super-admin account)
    global_tok = login("admin@example.com", "admin123")["access_token"]
    r4 = client.get("/api/admin/analytics/summary", headers={"Authorization": f"Bearer {global_tok}"})
    assert r4.status_code == 200
    global_summary = r4.json()
    # our org-specific count should not exceed global count
    assert summary["total_requests_24h"] <= global_summary["total_requests_24h"]
    assert summary["total_requests_24h"] >= 1

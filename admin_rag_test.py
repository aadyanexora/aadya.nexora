import os
import sys
import time

# make backend package importable from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@1234"


def seed_admin():
    # register user (if already exists this may error but we'll ignore)
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        r.raise_for_status()
    except Exception:
        pass

    # login to get token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    token = None
    try:
        token = r.json().get("access_token")
    except Exception:
        pass

    # promote the user to admin by touching database directly
    try:
        from app.db.session import SessionLocal
        from app.models.user import User

        db = SessionLocal()
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user and not user.is_admin:
            user.is_admin = True
            db.commit()
        db.close()
        print(f"Admin seeded or exists: {ADMIN_EMAIL}")
    except Exception as e:
        print("Failed to promote admin in DB:", e)
    return token


def test_admin_ingest(admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    sample_docs = {"texts": ["Mahabharata chapter 1", "Ramayana Sarga 1"]}
    try:
        r = requests.post(
            f"{BASE_URL}/api/admin/ingest", json=sample_docs, headers=headers
        )
        print("/admin/ingest response:", r.status_code, r.text)
    except Exception as e:
        print("Error calling admin ingest:", e)


def check_faiss_index():
    try:
        from app.rag.vector_store import FaissVectorStore

        vs = FaissVectorStore()
        print("FAISS index loaded. total vectors:", vs.index.ntotal)
    except Exception as e:
        print("Error loading FAISS index:", e)


def test_chat_stream(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"message": "Tell me about Bhagavad Gita chapter 2"}
    try:
        r = requests.post(
            f"{BASE_URL}/api/chat/stream", json=payload, headers=headers, stream=True
        )
        print("/chat/stream response status", r.status_code)
        for chunk in r.iter_lines():
            if chunk:
                try:
                    print(chunk.decode("utf-8"))
                except Exception:
                    print(chunk)
    except Exception as e:
        print("Error streaming chat:", e)


if __name__ == "__main__":
    token = seed_admin()
    if token:
        test_admin_ingest(token)
        test_chat_stream(token)
    else:
        print("Could not obtain token; skipping ingest/chat tests")
    check_faiss_index()

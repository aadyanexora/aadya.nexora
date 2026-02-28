import requests
import uuid

BASE = "http://localhost:8000"

def try_request():
    # generate unique email per run
    email = f"user+{uuid.uuid4()}@example.com"
    pwd = "password"

    print("\n--- POST /api/auth/register ---")
    r = requests.post(BASE + "/api/auth/register", json={"email": email, "password": pwd})
    print(r.status_code)
    print(r.text)

    print("\n--- POST /api/auth/login ---")
    r = requests.post(BASE + "/api/auth/login", json={"email": email, "password": pwd})
    print(r.status_code)
    print(r.text)
    token = None
    try:
        token = r.json().get("access_token")
    except Exception as e:
        print("parsing login json failed", e)
    print("token=", token)

    headers = {}
    if token:
        headers = {"Authorization": f"Bearer {token}"}
    print("headers=", headers)

    print("\n--- GET /api/auth/me ---")
    r = requests.get(BASE + "/api/auth/me", headers=headers)
    print(r.status_code)
    print(r.text)

    print("\n--- POST /api/admin/ingest ---")
    r = requests.post(
        BASE + "/api/admin/ingest",
        headers=headers,
        json={
            "texts": [
                "Aadya Nexora AI is a SaaS platform.",
                "It supports RAG and streaming chat."
            ]
        },
    )
    print(r.status_code)
    print(r.text)

    print("\n--- POST /api/chat/stream ---")
    r = requests.post(
        BASE + "/api/chat/stream",
        headers=headers,
        json={"message": "What is Aadya Nexora AI?"},
        stream=True,
    )
    print(r.status_code)
    count = 0
    for chunk in r.iter_lines():
        if chunk:
            print(chunk)
            count += 1
            if count >= 20:
                break


if __name__ == '__main__':
    try_request()

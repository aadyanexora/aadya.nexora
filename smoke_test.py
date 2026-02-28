import requests

BASE = "http://localhost:8000"

def try_request():
    print("Registering user...")
    r = requests.post(BASE + "/api/auth/register", json={"email":"test@example.com","password":"password"})
    print(r.status_code, r.text)

    print("Logging in user...")
    r = requests.post(BASE + "/api/auth/login", json={"email":"test@example.com","password":"password"})
    print(r.status_code, r.text)
    token = r.json().get("access_token")

    if token:
        headers = {"Authorization": f"Bearer {token}"}
        print("Calling /api/auth/me")
        r = requests.get(BASE + "/api/auth/me", headers=headers)
        print(r.status_code, r.text)

        print("Calling admin ingest")
        r = requests.post(BASE + "/api/admin/ingest", headers=headers, json={"texts": ["hello world."]})
        print(r.status_code, r.text)

        print("Streaming chat request")
        r = requests.post(BASE + "/api/chat/stream", headers=headers, json={"message": "hi"}, stream=True)
        print("stream status", r.status_code)
        for chunk in r.iter_lines():
            if chunk:
                print("chunk->", chunk)

if __name__ == '__main__':
    try_request()

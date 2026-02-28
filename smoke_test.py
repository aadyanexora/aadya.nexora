import requests
import uuid
import subprocess

BASE = "http://localhost:8000"


def log_if_server_error(resp):
    """If status code is 500, dump recent backend logs."""
    if resp is None:
        return
    if hasattr(resp, "status_code") and resp.status_code == 500:
        print("\n!!! Detected HTTP 500, fetching backend logs ...")
        try:
            output = subprocess.check_output(
                ["docker", "logs", "aadyanexora-backend-1", "--tail", "100"],
                stderr=subprocess.STDOUT,
                text=True,
            )
            print("---- backend logs ----")
            print(output)
            print("---- end backend logs ----")
        except Exception as e:
            print(f"Failed to get docker logs: {e}")


def try_request():
    # generate unique email per run
    email = f"user+{uuid.uuid4()}@example.com"
    pwd = "password"

    token = None
    headers = {}

    # helper to perform request with printing
    def do_request(method, url, **kwargs):
        nonlocal token, headers
        name = f"{method.upper()} {url.replace(BASE, '')}"
        print(f"\n========== {name} ==========")
        resp = None
        try:
            resp = requests.request(method, BASE + url, **kwargs)
            print("status_code:", resp.status_code)
            # print raw body
            if kwargs.get("stream"):
                # status code already printed; caller handles streaming
                pass
            else:
                try:
                    print(resp.text)
                except Exception:
                    print("<could not decode response text>")
        except Exception as exc:
            print(f"Exception during {name}: {exc}")
        log_if_server_error(resp)
        return resp

    # A) register
    r = do_request("post", "/api/auth/register", json={"email": email, "password": pwd})

    # B) login
    r = do_request("post", "/api/auth/login", json={"email": email, "password": pwd})
    if r is not None:
        try:
            token = r.json().get("access_token")
        except Exception as e:
            print("parsing login json failed", e)
    if token:
        headers = {"Authorization": f"Bearer {token}"}

    # C) auth/me
    do_request("get", "/api/auth/me", headers=headers)

    # D) ingest
    ingest_body = {
        "texts": [
            "Aadya Nexora AI is a SaaS AI platform.",
            "It uses local embeddings and Groq for chat."
        ]
    }
    do_request("post", "/api/admin/ingest", headers=headers, json=ingest_body)

    # E) chat/stream
    print(f"\n========== POST /api/chat/stream ==========")
    stream_resp = None
    try:
        stream_resp = requests.post(
            BASE + "/api/chat/stream",
            headers=headers,
            json={"message": "What is Aadya Nexora AI?"},
            stream=True,
        )
        print("status_code:", stream_resp.status_code)
        count = 0
        for chunk in stream_resp.iter_lines():
            # raw chunks already bytes; print repr to show raw bytes
            print(repr(chunk))
            count += 1
            if count >= 20:
                break
    except Exception as exc:
        print(f"Exception during streaming chat: {exc}")
    log_if_server_error(stream_resp)


if __name__ == '__main__':
    try_request()

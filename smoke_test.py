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

    access_token = None
    refresh_token = None
    headers = {}

    # helper to perform request with printing
    def do_request(method, url, **kwargs):
        nonlocal access_token, refresh_token, headers
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
    # include an organization name to exercise multi-tenant logic
    org = "smoke"
    r = do_request("post", "/api/auth/register", json={"email": email, "password": pwd, "organization": org})
    if r and r.status_code == 200:
        try:
            tok = r.json().get("access_token")
            import jwt, os
            orgid = jwt.decode(tok, os.environ.get("SECRET_KEY"), algorithms=["HS256"]).get("org_id")
            print("registered, org_id=", orgid)
        except Exception:
            pass

    # B) login
    r = do_request("post", "/api/auth/login", json={"email": email, "password": pwd})
    if r is not None:
        try:
            access_token = r.json().get("access_token")
            refresh_token = r.json().get("refresh_token")
        except Exception as e:
            print("parsing login json failed", e)
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}

    # C) auth/me
    do_request("get", "/api/auth/me", headers=headers)

    # D) health check (avoids heavy model downloads)
    do_request("get", "/health")

    # F) exercise refresh token using the refresh token returned by login
    if refresh_token:
        print("\n========== POST /api/auth/refresh ==========")
        print("using refresh token", refresh_token)
        r = do_request("post", "/api/auth/refresh", json={"refresh_token": refresh_token})
        if r is not None and r.status_code == 200:
            access_token = r.json().get("access_token")
            refresh_token = r.json().get("refresh_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            print("refresh succeeded, new access token obtained")
    # G) logout using the latest refresh token
    if refresh_token:
        print("\n========== POST /api/auth/logout ==========")
        do_request("post", "/api/auth/logout", json={"refresh_token": refresh_token})


if __name__ == '__main__':
    try_request()

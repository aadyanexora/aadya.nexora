from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def user_or_ip(request: Request):
    """Rate limiter key function that prefers authenticated user id."""
    uid = getattr(request.state, "user_id", None)
    if uid:
        return str(uid)
    return get_remote_address(request)


# shared limiter instance used by all routers that need rate limiting
limiter = Limiter(key_func=user_or_ip)

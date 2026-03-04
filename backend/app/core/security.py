from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from app.core.config import settings

# Use sha256_crypt only to avoid bcrypt runtime issues
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # bcrypt has 72-byte limit; truncate if necessary
    pw = password if isinstance(password, str) else str(password)
    if len(pw.encode('utf-8')) > 72:
        pw = pw[:72]
    return pwd_context.hash(pw)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: int = 15):
    """Create a signed JWT.

    * ``data`` should be a dictionary of claims (e.g. ``{"sub": ..., "role": ...}``).
    * ``expires_delta`` is minutes until expiration (default 15 minutes).
    The function will copy ``data`` and add ``iat``/``exp`` timestamps.
    """
    now = datetime.utcnow()
    to_encode = data.copy()
    to_encode.update({
        "iat": now,
        "exp": now + timedelta(minutes=expires_delta),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str):
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return data
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

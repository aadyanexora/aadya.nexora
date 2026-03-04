from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.config import settings
from datetime import datetime, timedelta
import secrets

router = APIRouter()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    role = "admin" if user.is_admin else "user"
    access = create_access_token(
        {"sub": str(user.id), "role": role},
        expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    raw_refresh = secrets.token_urlsafe(64)
    hashed = hash_password(raw_refresh)
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires, revoked=False)
    db.add(rt)
    db.commit()
    return {"access_token": access, "refresh_token": raw_refresh, "token_type": "bearer"}


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = "admin" if user.is_admin else "user"
    # generate tokens and save refresh
    access = create_access_token(
        {"sub": str(user.id), "role": role},
        expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    raw_refresh = secrets.token_urlsafe(64)
    hashed = hash_password(raw_refresh)
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires, revoked=False)
    db.add(rt)
    db.commit()
    return {"access_token": access, "refresh_token": raw_refresh, "token_type": "bearer"}

@router.get("/me")
def me(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    # Header will come in as "Bearer <token>"
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.split(" ")[-1]
    data = decode_access_token(token)
    user_id = data.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin, "credits": getattr(user, 'credits', None)}


@router.post("/refresh")
def refresh_token(payload: RefreshIn, db: Session = Depends(get_db)):
    # validate provided refresh token and rotate
    now = datetime.utcnow()
    # search for a non-revoked token that matches
    candidates = (
        db.query(RefreshToken)
        .filter(RefreshToken.revoked == False, RefreshToken.expires_at > now)
        .all()
    )
    for rt in candidates:
        if verify_password(payload.refresh_token, rt.token_hash):
            # rotate
            rt.revoked = True
            db.add(rt)
            user = db.query(User).filter(User.id == rt.user_id).first()
            if not user:
                break
            # issue new tokens
            role = "admin" if user.is_admin else "user"
            access = create_access_token(
                {"sub": str(user.id), "role": role},
                expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            )
            new_refresh = secrets.token_urlsafe(64)
            hashed = hash_password(new_refresh)
            expires2 = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            new_rt = RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires2, revoked=False)
            db.add(new_rt)
            db.commit()
            return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
def logout(payload: LogoutIn, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    tokens = (
        db.query(RefreshToken)
        .filter(RefreshToken.revoked == False, RefreshToken.expires_at > now)
        .all()
    )
    for rt in tokens:
        if verify_password(payload.refresh_token, rt.token_hash):
            rt.revoked = True
            db.add(rt)
            db.commit()
            return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid refresh token")

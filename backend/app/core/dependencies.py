from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.routes.chat import get_current_user
from app.models.user import User
from app.db.session import get_db


def admin_required(payload: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # get_current_user will raise 401 if the token is missing/invalid
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    # try to interpret subject as integer user id; if that fails we may be using
    # the simple "admin" string from the dummy login and there won't be a DB user.
    user_id = payload.get("sub")
    user = None
    try:
        uid = int(user_id) if user_id is not None else None
    except (ValueError, TypeError):
        uid = None
    if uid is not None:
        user = db.query(User).filter(User.id == uid).first()
    if user is None:
        # either no numeric id or user not found; but role claim says admin, so
        # we synthesize a minimal object to satisfy the type hint and allow
        # endpoints that don't actually use the user instance to proceed.
        class _DummyUser:
            def __init__(self):
                self.id = None
                self.is_admin = True
                self.organization_id = None
        return _DummyUser()
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

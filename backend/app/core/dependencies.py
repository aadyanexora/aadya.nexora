from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.routes.chat import get_current_user_optional as get_current_user
from app.models.user import User
from app.db.session import get_db


def admin_required(user_id: str | None = Depends(get_current_user), db: Session = Depends(get_db)):
    # get_current_user returns an optional user ID string
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    # fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

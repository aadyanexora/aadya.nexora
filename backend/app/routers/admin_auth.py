from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter(prefix="/admin", tags=["admin"])

# Request model
class LoginRequest(BaseModel):
    username: str
    password: str

# Response model
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Dummy in-memory admin credentials (replace with DB check if needed)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@router.post("/login", response_model=LoginResponse)
def admin_login(login: LoginRequest):
    if login.username == ADMIN_USERNAME and login.password == ADMIN_PASSWORD:
        # issue a real JWT rather than a hard‑coded string
        access_token = create_access_token(
            {"sub": login.username, "role": "admin"},
            expires_delta=60,
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

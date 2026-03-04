from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

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
        # generate a fake token for testing
        return {"access_token": "test_admin_token"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

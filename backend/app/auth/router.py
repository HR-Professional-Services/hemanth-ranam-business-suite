from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import sqlite3
from backend.app.core.database import get_db
from backend.app.core.security import verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    tenant_id: int
    tenant_name: str
    tenant_slug: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

def get_current_user(request: Request, db: sqlite3.Connection = Depends(get_db)) -> Dict[str, Any]:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    
    cur = db.cursor()
    cur.execute("""
    SELECT u.id, u.email, u.full_name, tm.role, tm.tenant_id, t.name as tenant_name, t.slug as tenant_slug
    FROM users u
    JOIN tenant_memberships tm ON tm.user_id = u.id
    JOIN tenants t ON t.id = tm.tenant_id
    WHERE u.id = ? AND tm.tenant_id = ? AND u.status = 'ACTIVE'
    """, (user_id, tenant_id))
    user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User or tenant context not found")

    return dict(user)

@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest, response: Response, db: sqlite3.Connection = Depends(get_db)):
    cur = db.cursor()
    cur.execute("""
    SELECT u.id, u.email, u.full_name, u.password_hash, tm.role, tm.tenant_id, t.name as tenant_name, t.slug as tenant_slug
    FROM users u
    JOIN tenant_memberships tm ON tm.user_id = u.id AND tm.is_default = 1
    JOIN tenants t ON t.id = tm.tenant_id
    WHERE u.email = ? AND u.status = 'ACTIVE'
    """, (creds.email,))
    user = cur.fetchone()

    if not user or not verify_password(creds.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token_data = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user["tenant_id"]
    }
    token = create_access_token(token_data)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=False
    )

    cur.execute("INSERT INTO audit_logs (user_id, tenant_id, action, resource, details) VALUES (?, ?, 'LOGIN', 'auth', 'Successful authentication')",
                (user["id"], user["tenant_id"]))
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "tenant_name": user["tenant_name"],
            "tenant_slug": user["tenant_slug"]
        }
    }

@router.post("/logout")
def logout(response: Response, user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    response.delete_cookie("access_token")
    cur = db.cursor()
    cur.execute("INSERT INTO audit_logs (user_id, tenant_id, action, resource, details) VALUES (?, ?, 'LOGOUT', 'auth', 'User logged out')",
                (user["id"], user["tenant_id"]))
    db.commit()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return user

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sqlite3
from backend.app.core.database import get_db
from backend.app.auth.router import get_current_user

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants"])

class TenantCreate(BaseModel):
    name: str
    slug: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#2563eb"
    currency: Optional[str] = "GBP"
    timezone: Optional[str] = "Europe/London"

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: Optional[str]
    primary_color: str
    currency: str
    timezone: str
    status: str
    created_at: str

@router.get("", response_model=List[TenantResponse])
def list_tenants(current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cur = db.cursor()
    # Super admins see all tenants, others only see their enrolled tenants
    if current_user["role"] == "SUPER_ADMIN":
        cur.execute("SELECT id, name, slug, logo_url, primary_color, currency, timezone, status, created_at FROM tenants ORDER BY id ASC")
    else:
        cur.execute("""
        SELECT t.id, t.name, t.slug, t.logo_url, t.primary_color, t.currency, t.timezone, t.status, t.created_at
        FROM tenants t
        JOIN tenant_memberships tm ON tm.tenant_id = t.id
        WHERE tm.user_id = ?
        ORDER BY t.id ASC
        """, (current_user["id"],))
    rows = cur.fetchall()
    return [dict(r) for r in rows]

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if current_user["role"] not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins or Admins can provision tenants")

    cur = db.cursor()
    cur.execute("SELECT id FROM tenants WHERE slug = ?", (payload.slug,))
    if cur.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant slug already exists")

    cur.execute("""
    INSERT INTO tenants (name, slug, logo_url, primary_color, currency, timezone, status)
    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
    """, (payload.name, payload.slug, payload.logo_url, payload.primary_color, payload.currency, payload.timezone))
    tenant_id = cur.lastrowid

    # Auto enroll creator as ADMIN for new tenant
    cur.execute("""
    INSERT INTO tenant_memberships (user_id, tenant_id, role, is_default)
    VALUES (?, ?, 'ADMIN', 0)
    """, (current_user["id"], tenant_id))

    # Enable all 7 applications for new tenant by default
    default_apps = ["crm", "accounts", "hrms", "erp", "helpdesk", "booking", "client-portal"]
    for slug in default_apps:
        cur.execute("""
        INSERT INTO tenant_applications (tenant_id, application_slug, is_enabled)
        VALUES (?, ?, 1)
        """, (tenant_id, slug))

    cur.execute("INSERT INTO audit_logs (user_id, tenant_id, action, resource, details) VALUES (?, ?, 'TENANT_CREATED', 'tenants', ?)",
                (current_user["id"], tenant_id, f"Created tenant {payload.name} ({payload.slug})"))
    db.commit()

    cur.execute("SELECT id, name, slug, logo_url, primary_color, currency, timezone, status, created_at FROM tenants WHERE id = ?", (tenant_id,))
    row = cur.fetchone()
    return dict(row)

@router.get("/{tenant_id}/verify-isolation")
def verify_tenant_isolation(tenant_id: int, current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    """Enforces strict isolation test: a user cannot query another tenant unless enrolled."""
    cur = db.cursor()
    cur.execute("SELECT id FROM tenant_memberships WHERE user_id = ? AND tenant_id = ?", (current_user["id"], tenant_id))
    membership = cur.fetchone()
    if not membership and current_user["role"] != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cross-tenant isolation barrier enforced")
    
    cur.execute("SELECT id, name, slug, status FROM tenants WHERE id = ?", (tenant_id,))
    tenant = cur.fetchone()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"status": "authorized", "tenant": dict(tenant)}

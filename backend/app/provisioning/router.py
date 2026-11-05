from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
import sqlite3
import json
from datetime import datetime, timezone
from backend.app.core.database import get_db
from backend.app.core.security import hash_password
from backend.app.auth.router import get_current_user

router = APIRouter(prefix="/api/v1/provisioning", tags=["Client Provisioning Engine"])

class ProvisionRequest(BaseModel):
    client_name: str
    client_slug: str
    admin_email: EmailStr
    admin_name: str
    admin_password: str
    primary_color: Optional[str] = "#2563eb"
    currency: Optional[str] = "GBP"
    timezone: Optional[str] = "Europe/London"
    enabled_modules: List[str] = ["crm", "accounts", "hrms", "erp", "helpdesk", "booking", "client-portal"]

class ProvisionJobResponse(BaseModel):
    id: int
    tenant_id: Optional[int]
    client_name: str
    admin_email: str
    status: str
    selected_modules: List[str]
    created_at: str
    completed_at: Optional[str]
    logs: Optional[str]

@router.get("/jobs", response_model=List[ProvisionJobResponse])
def list_provisioning_jobs(current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if current_user["role"] not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    cur = db.cursor()
    cur.execute("SELECT id, tenant_id, client_name, admin_email, selected_modules, status, logs, created_at, completed_at FROM provisioning_jobs ORDER BY id DESC")
    rows = cur.fetchall()
    return [{
        "id": r["id"],
        "tenant_id": r["tenant_id"],
        "client_name": r["client_name"],
        "admin_email": r["admin_email"],
        "status": r["status"],
        "selected_modules": json.loads(r["selected_modules"]) if r["selected_modules"] else [],
        "created_at": r["created_at"],
        "completed_at": r["completed_at"],
        "logs": r["logs"]
    } for r in rows]

@router.post("/provision", response_model=ProvisionJobResponse, status_code=status.HTTP_201_CREATED)
def provision_new_client(payload: ProvisionRequest, current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    if current_user["role"] not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    cur = db.cursor()
    
    # 1. Validation check
    cur.execute("SELECT id FROM tenants WHERE slug = ?", (payload.client_slug,))
    if cur.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant slug is already taken")

    # Record job
    modules_json = json.dumps(payload.enabled_modules)
    now_str = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO provisioning_jobs (client_name, admin_email, selected_modules, status, logs, created_at)
    VALUES (?, ?, ?, 'RUNNING', 'Provisioning started...', ?)
    """, (payload.client_name, payload.admin_email, modules_json, now_str))
    job_id = cur.lastrowid

    log_entries = ["Step 1: Created provisioning pipeline task"]

    try:
        # Step 2: Create Tenant
        cur.execute("""
        INSERT INTO tenants (name, slug, primary_color, currency, timezone, status)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (payload.client_name, payload.client_slug, payload.primary_color, payload.currency, payload.timezone))
        tenant_id = cur.lastrowid
        log_entries.append(f"Step 2: Tenant created with ID {tenant_id}")

        # Step 3: Create Client Admin User
        cur.execute("SELECT id FROM users WHERE email = ?", (payload.admin_email,))
        existing_user = cur.fetchone()
        if existing_user:
            user_id = existing_user[0]
            log_entries.append(f"Step 3: Linked existing user ID {user_id}")
        else:
            hashed_pw = hash_password(payload.admin_password)
            cur.execute("""
            INSERT INTO users (email, full_name, password_hash, role, status)
            VALUES (?, ?, ?, 'CLIENT_ADMIN', 'ACTIVE')
            """, (payload.admin_email, payload.admin_name, hashed_pw))
            user_id = cur.lastrowid
            log_entries.append(f"Step 3: New Client Admin user created with ID {user_id}")

        # Step 4: Create Tenant Membership
        cur.execute("""
        INSERT INTO tenant_memberships (user_id, tenant_id, role, is_default)
        VALUES (?, ?, 'CLIENT_ADMIN', 1)
        """, (user_id, tenant_id))
        log_entries.append("Step 4: Bound Client Admin to tenant membership")

        # Step 5: Enable Selected Modules
        for mod in payload.enabled_modules:
            cur.execute("""
            INSERT INTO tenant_applications (tenant_id, application_slug, is_enabled)
            VALUES (?, ?, 1)
            """, (tenant_id, mod))
        log_entries.append(f"Step 5: Provisioned {len(payload.enabled_modules)} application entitlements")

        # Step 6: Finalize Job
        completed_str = datetime.now(timezone.utc).isoformat()
        full_logs = "\n".join(log_entries) + "\n✓ Client ready for onboarding."
        cur.execute("""
        UPDATE provisioning_jobs
        SET tenant_id = ?, status = 'COMPLETED', logs = ?, completed_at = ?
        WHERE id = ?
        """, (tenant_id, full_logs, completed_str, job_id))

        cur.execute("INSERT INTO audit_logs (user_id, tenant_id, action, resource, details) VALUES (?, ?, 'CLIENT_PROVISIONED', 'provisioning', ?)",
                    (current_user["id"], tenant_id, f"Successfully provisioned client {payload.client_name}"))

        db.commit()

        return {
            "id": job_id,
            "tenant_id": tenant_id,
            "client_name": payload.client_name,
            "admin_email": payload.admin_email,
            "status": "COMPLETED",
            "selected_modules": payload.enabled_modules,
            "created_at": now_str,
            "completed_at": completed_str,
            "logs": full_logs
        }
    except Exception as e:
        db.rollback()
        cur.execute("""
        UPDATE provisioning_jobs
        SET status = 'FAILED', logs = ?
        WHERE id = ?
        """, (f"Provisioning error: {str(e)}", job_id))
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Provisioning failed: {str(e)}")

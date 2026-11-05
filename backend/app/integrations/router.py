from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import httpx
from backend.app.core.config import settings
from backend.app.auth.router import get_current_user

router = APIRouter(prefix="/api/v1/integrations", tags=["Service Adapters"])

@router.get("/overview")
async def get_consolidated_suite_overview(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Fetches real operational statistics across live services asynchronously."""
    stats = {
        "user": current_user["full_name"],
        "tenant": current_user["tenant_name"],
        "role": current_user["role"],
        "services": {}
    }

    async with httpx.AsyncClient(timeout=2.0) as client:
        # 1. Client Portal
        try:
            r = await client.get(f"{settings.CLIENT_PORTAL_URL}/api/dashboard/stats")
            stats["services"]["client_portal"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["client_portal"] = {"status": "offline"}

        # 2. Helpdesk
        try:
            r = await client.get(f"{settings.HELPDESK_URL}/api/dashboard/stats")
            stats["services"]["helpdesk"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["helpdesk"] = {"status": "offline"}

        # 3. CRM
        try:
            r = await client.get(f"{settings.CRM_URL}/api/dashboard/stats")
            stats["services"]["crm"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["crm"] = {"status": "offline"}

        # 4. Accounts
        try:
            r = await client.get(f"{settings.ACCOUNTS_URL}/api/dashboard/stats")
            stats["services"]["accounts"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["accounts"] = {"status": "offline"}

        # 5. HRMS
        try:
            r = await client.get(f"{settings.HRMS_URL}/api/dashboard/stats")
            stats["services"]["hrms"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["hrms"] = {"status": "offline"}

        # 6. ERP
        try:
            r = await client.get(f"{settings.ERP_URL}/api/dashboard/stats")
            stats["services"]["erp"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["erp"] = {"status": "offline"}

        # 7. Booking
        try:
            r = await client.get(f"{settings.BOOKING_URL}/api/dashboard/stats")
            stats["services"]["booking"] = r.json() if r.status_code == 200 else {"status": "degraded"}
        except Exception:
            stats["services"]["booking"] = {"status": "offline"}

    return stats

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sqlite3
import httpx
from backend.app.core.database import get_db
from backend.app.auth.router import get_current_user

router = APIRouter(prefix="/api/v1/applications", tags=["Applications Registry"])

class AppResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    category: str
    icon: str
    service_url: str
    default_port: int
    is_enabled: bool

class AppHealth(BaseModel):
    slug: str
    name: str
    service_url: str
    default_port: int
    status: str
    latency_ms: Optional[float] = None
    detail: Optional[str] = None

@router.get("", response_model=List[AppResponse])
def get_tenant_applications(current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cur = db.cursor()
    cur.execute("""
    SELECT a.id, a.slug, a.name, a.description, a.category, a.icon, a.service_url, a.default_port,
           COALESCE(ta.is_enabled, 1) as is_enabled
    FROM applications a
    LEFT JOIN tenant_applications ta ON ta.application_slug = a.slug AND ta.tenant_id = ?
    WHERE a.is_active = 1
    ORDER BY a.display_order ASC
    """, (current_user["tenant_id"],))
    rows = cur.fetchall()
    return [{
        "id": r["id"],
        "slug": r["slug"],
        "name": r["name"],
        "description": r["description"],
        "category": r["category"],
        "icon": r["icon"],
        "service_url": r["service_url"],
        "default_port": r["default_port"],
        "is_enabled": bool(r["is_enabled"])
    } for r in rows]

@router.get("/health-overview", response_model=List[AppHealth])
async def check_all_applications_health(current_user: Dict[str, Any] = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT slug, name, service_url, health_endpoint, default_port FROM applications WHERE is_active = 1 ORDER BY display_order ASC")
    apps = cur.fetchall()
    
    results = []
    async with httpx.AsyncClient(timeout=1.5) as client:
        for app in apps:
            health_url = f"{app['service_url']}{app['health_endpoint']}"
            try:
                start = httpx._types.time.time()
                res = await client.get(health_url)
                latency = round((httpx._types.time.time() - start) * 1000, 2)
                if res.status_code == 200:
                    status_str = "ONLINE"
                    detail = "Healthy"
                else:
                    status_str = "DEGRADED"
                    detail = f"HTTP {res.status_code}"
            except Exception as e:
                status_str = "OFFLINE"
                latency = None
                detail = "Unreachable"

            results.append({
                "slug": app["slug"],
                "name": app["name"],
                "service_url": app["service_url"],
                "default_port": app["default_port"],
                "status": status_str,
                "latency_ms": latency,
                "detail": detail
            })
    return results

# Master System Architecture & Deployment Specification
## Multi-Tenant Wildcard Domain Routing, Cloudflare Edge & Client Provisioning

**Document ID:** ARCH-SAAS-001  
**Authoritative Domain:** `hemanthranam.com`  
**Wildcard Scope:** `*.hemanthranam.com`  
**Owner:** Hemanth Ranam  
**Status:** ACTIVE & ENFORCED  
**Created:** 2026-11-05  

---

### 1. Unified Domain Model (`hemanthranam.com`)

The SaaS platform implements a single-domain multi-tenant wildcard architecture. Adding new clients incurs **zero incremental domain or DNS management overhead**:

```text
                           INTERNET
                              │
                              ▼
                     CLOUDFLARE EDGE
                  DNS / SSL / WAF / Turnstile
                              │
                      Wildcard CNAME (*)
                              │
                     *.hemanthranam.com
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
  app.hemanthranam.com                  {tenant}.hemanthranam.com
  (Central SaaS Control Plane)          (Client-Branded Environments)
          │                                       │
          │                                       ├── acme.hemanthranam.com
          │                                       ├── vanguard.hemanthranam.com
          │                                       ├── novacare.hemanthranam.com
          │                                       └── client100.hemanthranam.com
          ▼                                       ▼
  ┌───────────────────────────────────────────────────────────────┐
  │         FastAPI Hostname Tenant Middleware                     │
  │  1. Parse incoming `Host` header:                             │
  │     e.g., host = "acme.hemanthranam.com" -> slug = "acme"     │
  │  2. Fetch Tenant metadata, branding, enabled modules          │
  │  3. Strictly partition database queries via WHERE tenant_id   │
  └───────────────────────────────┬───────────────────────────────┘
                                  │
                   API / Service Gateway (:8000)
                                  │
     ┌──────────┬──────────┬──────┴───┬──────────┬──────────┐
     ▼          ▼          ▼          ▼          ▼          ▼
    CRM      Accounts     HRMS       ERP      Helpdesk   Booking
  (:8002)    (:8003)    (:8004)    (:8005)    (:8006)    (:8007)
                                                         │
                                                   Client Portal
                                                      (:8009)
```

---

### 2. Multi-Tenant Wildcard DNS Configuration

In the Cloudflare dashboard for `hemanthranam.com`:

| Type | Name | Target | Proxy Status | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **CNAME** | `@` (apex) | `cname.run.app` / Edge Origin | Proxied (Orange Cloud) | Root marketing site / agency portfolio |
| **CNAME** | `app` | `cname.run.app` / Edge Origin | Proxied (Orange Cloud) | Internal administrative control plane |
| **CNAME** | `*` (wildcard) | `cname.run.app` / Edge Origin | Proxied (Orange Cloud) | Dynamic auto-routing for all client subdomains |

- **SSL/TLS Mode:** Full (Strict) with Cloudflare Universal Edge SSL automatically covering `*.hemanthranam.com`.
- **Zero Incremental Cost:** Cloudflare wildcard subdomains and SSL certificates are 100% free with no per-tenant limits.

---

### 3. Dynamic Tenant Resolution Middleware

The central control plane resolves tenants dynamically on every inbound request without separate virtual hosts:

```python
# backend/app/core/middleware.py
from fastapi import Request, HTTPException
from backend.app.core.database import get_db_connection

async def tenant_resolution_middleware(request: Request, call_next):
    host = request.headers.get("host", "").lower().split(":")[0]
    subdomain = host.split(".")[0] if len(host.split(".")) > 2 else None
    
    # Exclude system subdomains
    if subdomain in ["app", "admin", "api", "www", None]:
        request.state.tenant = None
        request.state.tenant_slug = "master"
    else:
        # Resolve tenant dynamically from DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, slug, status, primary_color FROM tenants WHERE slug = ?", (subdomain,))
        tenant = cur.fetchone()
        conn.close()
        
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Client tenant '{subdomain}' does not exist.")
        if tenant["status"] != "ACTIVE":
            raise HTTPException(status_code=403, detail="Client tenant account is suspended or inactive.")
            
        request.state.tenant = dict(tenant)
        request.state.tenant_slug = subdomain

    return await call_next(request)
```

---

### 4. Client Provisioning Workflow

When an administrator provisions a new client inside `app.hemanthranam.com`:

1. **Input:** Admin enters `Company Name`, `Slug` (e.g. `acme`), `Admin Email`, and selects enabled modules (e.g. CRM, Helpdesk, Client Portal).
2. **Database Mutation:**
   - Creates row in `tenants` table (`slug = 'acme'`).
   - Creates row in `users` with `CLIENT_ADMIN` role.
   - Creates membership binding `users.id` + `tenants.id`.
   - Populates `tenant_applications` entitlement table with selected modules.
3. **Instant Activation:**
   - Client is immediately accessible at `https://acme.hemanthranam.com`.
   - **No DNS modifications required** (handled by the wildcard CNAME `*.hemanthranam.com`).
   - Client sees custom brand styling and only their entitled modules.

---

### 5. Verified Local Port Matrix

| Service | Repository | Local Port | Health Endpoint | Stack |
| :--- | :--- | :--- | :--- | :--- |
| **Control Plane** | `hemanth-ranam-business-suite` | `:8000` | `/health` | FastAPI + SQLite / PostgreSQL |
| **CRM Pipeline** | `hemanth-ranam-crm` | `:8002` | `/api/health` | FastAPI + SQLite WAL |
| **Accounts & Invoicing** | `hemanth-ranam-accounts` | `:8003` | `/api/health` | FastAPI + SQLite WAL |
| **HRMS Engine** | `hemanth-ranam-hrms` | `:8004` | `/api/health` | FastAPI + SQLite WAL |
| **ERP Suite** | `hemanth-ranam-erp` | `:8005` | `/api/health` | FastAPI + SQLite WAL |
| **Helpdesk & SLAs** | `hemanth-ranam-helpdesk` | `:8006` | `/api/health` | FastAPI + SQLite WAL |
| **Booking Engine** | `hemanth-ranam-booking` | `:8007` | `/api/health` | FastAPI + SQLite WAL |
| **Client Portal** | `hemanth-ranam-client-portal` | `:8009` | `/api/health` | FastAPI + SQLite WAL |

---

### 6. Free-Tier Production Infrastructure Mapping

| Layer | Recommended Provider | Free Monthly Quota | Production Role |
| :--- | :--- | :--- | :--- |
| **DNS / Edge / SSL** | **Cloudflare Free** | Unlimited requests & bandwidth | Wildcard DNS (`*.hemanthranam.com`), SSL, DDoS & Turnstile |
| **ASGI Compute** | **Google Cloud Run** | 2,000,000 requests/mo, 360k vCPU-sec | Serverless container execution for FastAPI control plane |
| **Database** | **Neon / Supabase Free** | 500 MB PostgreSQL + 100 pool connections | Multi-tenant persistent relational database |
| **Static Frontends** | **Cloudflare Pages** | Unlimited bandwidth, 100 builds/mo | Static admin/client single-page frontends |

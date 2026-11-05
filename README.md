# HR Professional Services — Unified SaaS Control Plane

[![CI Quality Gate](https://github.com/HR-Professional-Services/hemanth-ranam-business-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/HR-Professional-Services/hemanth-ranam-business-suite/actions)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-blue.svg)](LICENSE)

The central SaaS operating system and control plane for **HR Professional Services Ltd** (Company Operating Hub). This platform orchestrates seven specialized business engines with centralized authentication, multi-tenant RBAC, cross-service navigation, real-time health observability, and automated client provisioning.

---

## 1. System Architecture

The Business Suite adopts a **Hub & Spoke** architecture:

```text
                    HR PROFESSIONAL SERVICES
                            │
                            ▼
                 ┌─────────────────────┐
                 │   BUSINESS SUITE    │
                 │   CONTROL PLANE     │ (:8000)
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
       Identity          Tenants          Administration
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                    Unified Dashboard
                            │
        ┌──────────┬───────┼───────┬──────────┐
        ▼          ▼       ▼       ▼          ▼
       CRM      Helpdesk Accounts HRMS       ERP
      (:8002)    (:8006)  (:8003) (:8004)   (:8005)
        │          │       │       │          │
        └──────────┴───────┼───────┴──────────┘
                            │
                         Booking (:8007)
                            │
                       Client Portal (:8009)
```

### The Seven Connected Engines
1. **Client Portal (`:8009`):** Client onboarding dashboard, deliverables tracker, contracts & document vault.
2. **Helpdesk & SLAs (`:8006`):** Omnichannel customer ticketing, SLA compliance engine & knowledge base.
3. **CRM Pipeline (`:8002`):** Lead scoring, visual Kanban pipelines, deal progression stages & client interactions.
4. **Accounts & Invoicing (`:8003`):** Quotations, automated VAT invoices, expenses & multi-currency ledger.
5. **HRMS Engine (`:8004`):** Employee records, attendance, leave approvals & compliance vault.
6. **ERP Suite (`:8005`):** Multi-tenant tenant registry, inventory, supplier management & core operations.
7. **Booking Engine (`:8007`):** Real-time calendar scheduling, staff availability & client intake booking.

---

## 2. Key Capabilities

- **Unified Identity & RBAC:** Single session authentication via signed JWTs. Granular roles: `SUPER_ADMIN`, `ADMIN`, `MANAGER`, `STAFF`, `CLIENT_ADMIN`, `CLIENT_USER`.
- **Enforced Multi-Tenancy:** Row-level tenant partitioning verified via automated cross-tenant security barriers.
- **Automated Client Provisioning:** One-click onboarding pipeline provisioning tenant records, tenant admins, and module entitlements.
- **Service Adapters:** Asynchronous HTTP adapters querying live microservices without direct foreign database manipulation.
- **Zero Mandatory Paid Infrastructure:** Built free-tier-first for Cloudflare Pages/Workers, SQLite/PostgreSQL, and containerized ASGI runtimes.

---

## 3. Quick Start (Local Development)

### Prerequisites
- Python 3.12+
- `uv` package manager

### Launching the Control Plane
```powershell
# Clone repository
git clone https://github.com/HR-Professional-Services/hemanth-ranam-business-suite.git
cd hemanth-ranam-business-suite

# Install dependencies
uv pip install -r requirements.txt

# Start control plane daemon on port 8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Access the unified dashboard at: [http://localhost:8000](http://localhost:8000)  
Interactive OpenAPI documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Automated Testing & Verification
```powershell
python -m pytest backend/tests/test_control_plane.py -v
```

Includes verification for:
- Root health probe (`/health`)
- Authentication & JWT session issuance
- Invalid credential rejection
- Multi-tenant creation & automated client provisioning
- **Strict cross-tenant access rejection (403 Forbidden verification)**

import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "version" in data

def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@hrservices.com",
        "password": "AdminSecure2026!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@hrservices.com"
    assert data["user"]["role"] == "SUPER_ADMIN"

def test_login_invalid_credentials():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@hrservices.com",
        "password": "WrongPassword123"
    })
    assert response.status_code == 401

def test_tenant_creation_and_isolation():
    uid = uuid.uuid4().hex[:6]
    # 1. Login as Super Admin
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@hrservices.com",
        "password": "AdminSecure2026!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Tenant A
    res_a = client.post("/api/v1/tenants", json={
        "name": f"Alpha Corp {uid}",
        "slug": f"alpha-corp-{uid}",
        "primary_color": "#10b981",
        "currency": "GBP"
    }, headers=headers)
    assert res_a.status_code == 201
    tenant_a_id = res_a.json()["id"]

    # 3. Create Tenant B via Provisioning
    prov_res = client.post("/api/v1/provisioning/provision", json={
        "client_name": f"Beta Logistics {uid}",
        "client_slug": f"beta-logistics-{uid}",
        "admin_email": f"admin-{uid}@betalogistics.com",
        "admin_name": "Marcus Vance",
        "admin_password": "BetaSecure2026!"
    }, headers=headers)
    assert prov_res.status_code == 201
    tenant_b_id = prov_res.json()["tenant_id"]

    # 4. Login as Tenant B User
    user_b_res = client.post("/api/v1/auth/login", json={
        "email": f"admin-{uid}@betalogistics.com",
        "password": "BetaSecure2026!"
    })
    assert user_b_res.status_code == 200
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 5. SECURITY GATE: Tenant B user attempts to access Tenant A isolation barrier
    unauthorized_res = client.get(f"/api/v1/tenants/{tenant_a_id}/verify-isolation", headers=headers_b)
    # Expected: 403 Forbidden strictly enforced
    assert unauthorized_res.status_code == 403
    assert "Cross-tenant isolation barrier enforced" in unauthorized_res.json()["detail"]

    # 6. Tenant B user accessing own tenant
    authorized_res = client.get(f"/api/v1/tenants/{tenant_b_id}/verify-isolation", headers=headers_b)
    assert authorized_res.status_code == 200
    assert authorized_res.json()["tenant"]["slug"] == f"beta-logistics-{uid}"

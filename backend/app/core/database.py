import sqlite3
import os
from backend.app.core.config import settings
from backend.app.core.security import hash_password

def get_db():
    db_path = settings.DATABASE_PATH
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    db_path = settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Tenants
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        logo_url TEXT,
        primary_color TEXT DEFAULT '#2563eb',
        currency TEXT DEFAULT 'GBP',
        timezone TEXT DEFAULT 'Europe/London',
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT DEFAULT (datetime('now', 'utc'))
    )
    """)
    
    # 2. Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'STAFF',
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT DEFAULT (datetime('now', 'utc'))
    )
    """)
    
    # 3. Tenant Memberships
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenant_memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tenant_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        is_default INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now', 'utc')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        UNIQUE (user_id, tenant_id)
    )
    """)
    
    # 4. Applications Registry
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        icon TEXT NOT NULL,
        service_url TEXT NOT NULL,
        health_endpoint TEXT NOT NULL,
        default_port INTEGER NOT NULL,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0
    )
    """)
    
    # 5. Tenant Application Entitlements
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenant_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        application_slug TEXT NOT NULL,
        is_enabled INTEGER DEFAULT 1,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        UNIQUE(tenant_id, application_slug)
    )
    """)

    # 6. Audit Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tenant_id INTEGER,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        created_at TEXT DEFAULT (datetime('now', 'utc'))
    )
    """)

    # 7. Provisioning Jobs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS provisioning_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER,
        client_name TEXT NOT NULL,
        admin_email TEXT NOT NULL,
        selected_modules TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        logs TEXT,
        created_at TEXT DEFAULT (datetime('now', 'utc')),
        completed_at TEXT
    )
    """)
    
    conn.commit()

    # Seed Default Tenant & SuperAdmin if not exists
    cur.execute("SELECT id FROM tenants WHERE slug = 'hr-master'")
    master_tenant = cur.fetchone()
    if not master_tenant:
        cur.execute("""
        INSERT INTO tenants (name, slug, logo_url, primary_color, currency, timezone, status)
        VALUES ('HR Professional Services Ltd', 'hr-master', '/static/logo.svg', '#2563eb', 'GBP', 'Europe/London', 'ACTIVE')
        """)
        tenant_id = cur.lastrowid
    else:
        tenant_id = master_tenant[0]

    cur.execute("SELECT id FROM users WHERE email = 'admin@hrservices.com'")
    admin_user = cur.fetchone()
    if not admin_user:
        hashed = hash_password("AdminSecure2026!")
        cur.execute("""
        INSERT INTO users (email, full_name, password_hash, role, status)
        VALUES ('admin@hrservices.com', 'Hemanth Ranam', ?, 'SUPER_ADMIN', 'ACTIVE')
        """, (hashed,))
        user_id = cur.lastrowid
        
        cur.execute("""
        INSERT INTO tenant_memberships (user_id, tenant_id, role, is_default)
        VALUES (?, ?, 'SUPER_ADMIN', 1)
        """, (user_id, tenant_id))

    # Seed Application Registry
    default_apps = [
        ("crm", "CRM Pipeline", "Lead scoring, visual pipelines, deal progression & follow-ups", "Sales", "Target", settings.CRM_URL, "/api/health", 8002, 1),
        ("accounts", "Accounts & Invoicing", "Quotations, automated VAT invoices, expenses & payments", "Finance", "CreditCard", settings.ACCOUNTS_URL, "/api/health", 8003, 2),
        ("hrms", "HRMS Engine", "Employee records, attendance, leave approvals & payroll", "Operations", "Users", settings.HRMS_URL, "/api/health", 8004, 3),
        ("erp", "ERP Suite", "Multi-tenant tenant registry, inventory & business backbone", "Operations", "Layers", settings.ERP_URL, "/api/health", 8005, 4),
        ("helpdesk", "Helpdesk & SLAs", "Omnichannel support ticketing, SLA timer compliance & KB", "Support", "LifeBuoy", settings.HELPDESK_URL, "/api/health", 8006, 5),
        ("booking", "Booking Engine", "Real-time calendar scheduling, staff availability & client intake", "Scheduling", "Calendar", settings.BOOKING_URL, "/api/health", 8007, 6),
        ("client-portal", "Client Portal", "Client onboarding dashboard, milestone tracker & documents", "Client", "LayoutDashboard", settings.CLIENT_PORTAL_URL, "/api/health", 8009, 7)
    ]

    for slug, name, desc, cat, icon, url, health, port, order in default_apps:
        cur.execute("SELECT id FROM applications WHERE slug = ?", (slug,))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO applications (slug, name, description, category, icon, service_url, health_endpoint, default_port, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (slug, name, desc, cat, icon, url, health, port, order))
            
        cur.execute("SELECT id FROM tenant_applications WHERE tenant_id = ? AND application_slug = ?", (tenant_id, slug))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO tenant_applications (tenant_id, application_slug, is_enabled)
            VALUES (?, ?, 1)
            """, (tenant_id, slug))

    conn.commit()
    conn.close()

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.auth.router import router as auth_router
from backend.app.tenants.router import router as tenants_router
from backend.app.applications.router import router as apps_router
from backend.app.provisioning.router import router as prov_router
from backend.app.integrations.router import router as integrations_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Mount API Routers
app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(apps_router)
app.include_router(prov_router)
app.include_router(integrations_router)

# Health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0"
    }

# Serve Unified SaaS Admin UI
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

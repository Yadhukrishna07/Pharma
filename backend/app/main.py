from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends
from sqlalchemy.orm import Session
from app.auth import get_current_user, require_roles
from app.database import engine, Base, get_db
from app.models.schemas import User
import os
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="PharmMedian — Closed-Loop Drug Return Platform",
    description="Enterprise-grade pharmaceutical return, destruction & audit management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for evidence uploads — disabled on Vercel (read-only filesystem)
# TODO: switch to cloud storage (Vercel Blob / S3 / Supabase) for uploads in production
if os.environ.get("VERCEL") != "1":
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
from app.api import auth, batches, returns, disputes, destruction, certificates, audit, dashboard, evidence, chatbot, reallocation

# Register routers
app.include_router(auth.router)
app.include_router(batches.router)
app.include_router(returns.router)
app.include_router(disputes.router)
app.include_router(destruction.router)
app.include_router(destruction.mfg_router)
app.include_router(certificates.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(evidence.router)
<<<<<<< HEAD
app.include_router(telegram.router)
=======
app.include_router(chatbot.router)
app.include_router(reallocation.router)


@app.get("/notifications")
def get_notifications_root(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notifications for current user (filtered by user.id). All authenticated."""
    from app.services.notification_service import get_user_notifications
    from app.models.schemas import NotificationResponse
    notifs = get_user_notifications(db, current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifs]


@app.get("/moderator/events")
def get_moderator_events_root(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("REGULATOR")),
):
    """Get all AI moderator events. REGULATOR only."""
    from app.models.schemas import ModeratorEvent, ModeratorEventResponse
    events = db.query(ModeratorEvent).order_by(ModeratorEvent.id.desc()).all()
    return [ModeratorEventResponse.model_validate(e) for e in events]


@app.get("/")
def root():
    return {
        "name": "PharmMedian API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
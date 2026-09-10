from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api import auth, batches, returns, disputes, destruction, certificates, audit


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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(batches.router)
app.include_router(returns.router)
app.include_router(disputes.router)
app.include_router(destruction.router)
app.include_router(certificates.router)
app.include_router(audit.router)


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

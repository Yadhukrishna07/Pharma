"""
API router for Supply-Demand Redistribution and Stock Reallocation.
Authenticated endpoints for viewing AI & deterministic transfer proposals.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.schemas import User
from app.services.reallocation_service import get_reallocation_recommendations, get_reallocation_data

router = APIRouter(prefix="/reallocation", tags=["reallocation"])


@router.get("/recommendations")
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get smart inter-pharmacy inventory transfer recommendations.
    Uses Gemini AI optimization with deterministic fallback.
    """
    return get_reallocation_recommendations(db)


@router.get("/raw-data")
def get_raw_reallocation_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get raw demand bottlenecks and near-expiry surplus datasets.
    """
    return get_reallocation_data(db)

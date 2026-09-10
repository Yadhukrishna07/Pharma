from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models.schemas import (
    User, UserRole, LoginRequest, RegisterRequest, TokenResponse,
    UserResponse, RoleSwitchRequest,
)
from app.services.notification_service import get_unread_count

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(User).filter(
        (User.username == req.username) | (User.email == req.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role,
        organization_name=req.organization_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/switch-role", response_model=TokenResponse)
def switch_role(req: RoleSwitchRequest, db: Session = Depends(get_db)):
    """
    Demo convenience: switch to a user with the specified role.
    Finds the first user matching that role and returns their token.
    """
    user = db.query(User).filter(User.role == req.role).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found with role {req.role.value}")

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/notifications/count")
def notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get unread notification count for current user."""
    count = get_unread_count(db, current_user.id)
    return {"count": count}


@router.get("/notifications")
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notifications for the current user."""
    from app.services.notification_service import get_user_notifications
    from app.models.schemas import NotificationResponse
    notifs = get_user_notifications(db, current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    from app.services.notification_service import mark_notification_read
    notif = mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()
    return {"status": "ok"}

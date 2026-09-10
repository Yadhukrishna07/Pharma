import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.schemas import Notification, User, UserRole


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
) -> Notification:
    """Create a notification for a specific user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        read_status=False,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(notif)
    return notif


def notify_by_role(
    db: Session,
    roles: List[str],
    title: str,
    message: str,
) -> List[Notification]:
    """Send notifications to all users matching the given roles."""
    notifications = []
    role_enums = []
    for r in roles:
        try:
            role_enums.append(UserRole(r))
        except ValueError:
            continue

    users = db.query(User).filter(User.role.in_(role_enums)).all()
    for user in users:
        notif = create_notification(db, user.id, title, message)
        notifications.append(notif)
    return notifications


def get_user_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
) -> List[Notification]:
    """Get notifications for a user, optionally filtered to unread only."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read_status == False)
    return query.order_by(Notification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id: int) -> Optional[Notification]:
    """Mark a notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if notif:
        notif.read_status = True
    return notif


def get_unread_count(db: Session, user_id: int) -> int:
    """Return the count of unread notifications for a user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read_status == False)
        .count()
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.db.models import User, Notification
from app.core.security import get_current_user
from datetime import datetime

router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
)

@router.get("")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20
):
    """Fetch notifications for the current user."""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(limit).all()
    
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "type": notif.type,
                "link": notif.link,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else None
            }
            for notif in notifications
        ]
    }

@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
    notification.is_read = True
    db.commit()
    
    return {"success": True}

@router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read for the current user."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    return {"success": True}

@router.post("/{notification_id}/delete")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"success": True}

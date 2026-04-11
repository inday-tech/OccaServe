from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List
from ..db import database, models, schemas
from ..core import security as auth
from ..services.realtime import manager
import os
import uuid
from fastapi import UploadFile, File
from datetime import datetime

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/history/{other_user_id}", response_model=List[schemas.ChatMessageResponse])
async def get_chat_history(
    other_user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Fetch chat history between current user and another user."""
    messages = db.query(models.ChatMessage).filter(
        or_(
            and_(models.ChatMessage.sender_id == current_user.id, models.ChatMessage.receiver_id == other_user_id),
            and_(models.ChatMessage.sender_id == other_user_id, models.ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(models.ChatMessage.created_at.asc()).all()
    
    return messages

@router.get("/conversations")
async def get_conversations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """List all unique users the current user has chatted with, plus the last message."""
    # This is a bit more complex in SQL. We'll find all unique pairs.
    # We can use a subquery to find the latest message per peer.
    
    # Peer ID is either sender or receiver (whichever is not current_user)
    # We'll fetch all messages involving current_user and then group in Python for simplicity in this MVP
    all_msgs = db.query(models.ChatMessage).filter(
        or_(models.ChatMessage.sender_id == current_user.id, models.ChatMessage.receiver_id == current_user.id)
    ).order_by(models.ChatMessage.created_at.desc()).all()
    
    conversations = {}
    for msg in all_msgs:
        peer_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if peer_id not in conversations:
            peer = db.query(models.User).get(peer_id)
            if not peer: continue
            
            peer_info = {
                "id": peer.id,
                "name": f"{peer.first_name} {peer.last_name}" if peer.first_name else peer.email,
                "email": peer.email,
                "role": peer.role,
                "profile_image": peer.profile_image_url
            }
            
            # If peer is a caterer, add business name
            if peer.role == 'caterer' and peer.caterer_profile:
                peer_info["name"] = peer.caterer_profile.business_name
                peer_info["logo"] = peer.caterer_profile.logo_url
                
            conversations[peer_id] = {
                "peer": peer_info,
                "last_message": {
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "file_name": msg.file_name,
                    "created_at": msg.created_at,
                    "sender_id": msg.sender_id,
                    "is_read": msg.is_read
                },
                "unread_count": 0
            }
        
        if not msg.is_read and msg.receiver_id == current_user.id:
            conversations[peer_id]["unread_count"] += 1
            
    return list(conversations.values())

@router.post("/send", response_model=schemas.ChatMessageResponse)
async def send_message(
    chat_msg: schemas.ChatMessageCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Save a message and broadcast via WebSocket."""
    # Verify receiver exists
    receiver = db.query(models.User).get(chat_msg.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
        
    db_msg = models.ChatMessage(
        sender_id=current_user.id,
        receiver_id=chat_msg.receiver_id,
        content=chat_msg.content,
        message_type=chat_msg.message_type,
        file_url=chat_msg.file_url,
        file_name=chat_msg.file_name
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    
    # Broadcast to receiver
    msg_data = {
        "type": "chat_message",
        "id": db_msg.id,
        "sender_id": db_msg.sender_id,
        "sender_name": f"{current_user.first_name} {current_user.last_name}" if current_user.first_name else current_user.email,
        "content": db_msg.content,
        "message_type": db_msg.message_type,
        "file_url": db_msg.file_url,
        "file_name": db_msg.file_name,
        "created_at": db_msg.created_at.isoformat(),
        "is_read": db_msg.is_read
    }
    
    # If sender is caterer, use business name
    if current_user.role == 'caterer' and current_user.caterer_profile:
        msg_data["sender_name"] = current_user.caterer_profile.business_name

    import asyncio
    asyncio.create_task(manager.broadcast_to_user(chat_msg.receiver_id, msg_data))
    
    return db_msg

@router.get("/unread-count")
async def get_total_unread_count(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get the total number of unread messages for the current user."""
    count = db.query(models.ChatMessage).filter(
        models.ChatMessage.receiver_id == current_user.id,
        models.ChatMessage.is_read == False
    ).count()
    return {"count": count}

@router.post("/read/{message_id}")
async def mark_as_read(
    message_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark a message as read."""
    msg = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == message_id,
        models.ChatMessage.receiver_id == current_user.id
    ).first()
    
    if msg:
        msg.is_read = True
        db.commit()
        return {"status": "success"}
    
    raise HTTPException(status_code=404, detail="Message not found or not authorized")

@router.post("/read-all/{peer_id}")
async def mark_all_as_read(
    peer_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark all messages from a specific peer as read."""
    db.query(models.ChatMessage).filter(
        models.ChatMessage.sender_id == peer_id,
        models.ChatMessage.receiver_id == current_user.id,
        models.ChatMessage.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success"}

@router.patch("/edit/{message_id}", response_model=schemas.ChatMessageResponse)
async def edit_message(
    message_id: int,
    chat_msg: schemas.ChatMessageBase,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Edit an existing message."""
    db_msg = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == message_id,
        models.ChatMessage.sender_id == current_user.id
    ).first()
    
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")
    
    if db_msg.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot edit a deleted message")

    # Time-based edit restriction (10 minutes)
    from datetime import datetime, timezone
    message_age = (datetime.now(timezone.utc) - db_msg.created_at).total_seconds()
    if message_age > 600: # 10 minutes = 600 seconds
        raise HTTPException(status_code=400, detail="Edit window has expired (10 minutes max)")

    db_msg.content = chat_msg.content
    db_msg.is_edited = True
    db.commit()
    db.refresh(db_msg)
    
    # Broadcast edit to receiver
    edit_data = {
        "type": "message_edit",
        "id": db_msg.id,
        "content": db_msg.content,
        "sender_id": db_msg.sender_id,
        "receiver_id": db_msg.receiver_id
    }
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(db_msg.receiver_id, edit_data))
    
    return db_msg

@router.delete("/delete/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Soft delete a message."""
    db_msg = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == message_id,
        models.ChatMessage.sender_id == current_user.id
    ).first()
    
    if not db_msg:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")
    
    db_msg.is_deleted = True
    db.commit()
    
    # Broadcast delete to receiver
    delete_data = {
        "type": "message_delete",
        "id": db_msg.id,
        "sender_id": db_msg.sender_id,
        "receiver_id": db_msg.receiver_id
    }
    import asyncio
    asyncio.create_task(manager.broadcast_to_user(db_msg.receiver_id, delete_data))
    
    return {"status": "success", "id": message_id}

@router.post("/upload")
async def upload_chat_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Upload a file to the chat directory."""
    # Ensure directory exists
    chat_upload_dir = os.path.join("app", "static", "uploads", "chat")
    os.makedirs(chat_upload_dir, exist_ok=True)
    
    # Security: limit file types (Optional but recommended)
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.docx', '.txt', '.webp']
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(chat_upload_dir, filename)
    
    # Write file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {
        "file_url": f"/static/uploads/chat/{filename}",
        "file_name": file.filename,
        "message_type": "image" if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else "file"
    }

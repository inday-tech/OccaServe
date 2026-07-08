from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from typing import List, Optional
from sqlalchemy.orm import Session
from ..db import database, models, schemas
from ..core import security as auth
import os
import shutil
import uuid

router = APIRouter(prefix="/caterer/api", tags=["caterer_feed"])

UPLOAD_DIR = "app/static/uploads/caterer/posts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Dependency to ensure only caterers can manage their feed
caterer_only = auth.RoleChecker(["caterer"])

@router.get("/posts/{caterer_id}", response_model=List[schemas.SocialPostResponse])
async def get_caterer_posts(
    caterer_id: int, 
    db: Session = Depends(database.get_db)
):
    posts = db.query(models.SocialPost).filter(
        models.SocialPost.caterer_id == caterer_id
    ).order_by(models.SocialPost.created_at.desc()).all()
    return posts

@router.post("/posts", response_model=schemas.SocialPostResponse)
async def create_social_post(
    content: str = Form(...),
    post_type: str = Form("general"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    if not user.caterer_profile:
        raise HTTPException(status_code=400, detail="User has no caterer profile")
    
    image_url = None
    if image:
        import base64
        content_bytes = await image.read()
        b64 = base64.b64encode(content_bytes).decode('utf-8')
        mime = image.content_type or 'image/jpeg'
        image_url = f"data:{mime};base64,{b64}"

    new_post = models.SocialPost(
        caterer_id=user.caterer_profile.id,
        content=content,
        post_type=post_type,
        image_url=image_url
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@router.delete("/posts/{post_id}")
async def delete_social_post(
    post_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    post = db.query(models.SocialPost).filter(
        models.SocialPost.id == post_id,
        models.SocialPost.caterer_id == user.caterer_profile.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or unauthorized")
    
    # No local file deletion needed for base64
            
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}

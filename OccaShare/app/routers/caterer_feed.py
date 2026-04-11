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
        # Save image
        ext = image.filename.split(".")[-1]
        filename = f"post_{uuid.uuid4()}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        image_url = f"/static/uploads/caterer/posts/{filename}"

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
    
    # Optional: Delete physical image file
    if post.image_url:
        filename = post.image_url.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}

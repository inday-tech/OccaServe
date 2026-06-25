import os
import uuid
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from PIL import Image

from app.db import database, models
from app.core.security import get_current_user, RoleChecker
from app.core.templates import templates
caterer_only = RoleChecker(["caterer"])

router = APIRouter(prefix="/caterer/portfolio", tags=["portfolio"])

UPLOAD_DIR = "app/static/uploads/portfolios"
THUMBNAIL_DIR = "app/static/uploads/portfolios/thumbnails"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

def process_and_save_image(file: UploadFile, is_cover: bool = False) -> str:
    """Compresses image to WebP and generates a thumbnail if it's a cover photo."""
    try:
        content = file.file.read()
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (e.g., from RGBA or P)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        filename = f"{uuid.uuid4()}.webp"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Save compressed high-res image (max 1920x1080)
        image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
        image.save(filepath, "WEBP", quality=85)
        
        if is_cover:
            # Generate a 600x600 thumbnail for the landing page
            thumb = image.copy()
            thumb.thumbnail((600, 600), Image.Resampling.LANCZOS)
            thumb_filename = f"thumb_{filename}"
            thumbnail_filepath = os.path.join(THUMBNAIL_DIR, thumb_filename)
            thumb.save(thumbnail_filepath, "WEBP", quality=80)
            
        return f"/static/uploads/portfolios/{filename}"
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file format")

@router.get("/", response_class=HTMLResponse)
async def manage_portfolio_page(
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    portfolios = db.query(models.Portfolio).filter(models.Portfolio.caterer_id == profile.id).order_by(models.Portfolio.created_at.desc()).all()
    
    # Also fetch completed bookings for linking
    completed_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.status.in_(["Completed", "Delivered"])
    ).all()
    
    return templates.TemplateResponse(
        "caterer/portfolio.html", 
        {
            "request": request, 
            "user": user, 
            "profile": profile, 
            "portfolios": portfolios,
            "completed_bookings": completed_bookings
        }
    )

@router.post("/create")
async def create_portfolio(
    title: str = Form(...),
    event_type: str = Form(...),
    description: str = Form(...),
    highlights: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    event_date: Optional[str] = Form(None),
    visibility: str = Form("Public"),
    is_featured: bool = Form(False),
    booking_id: Optional[int] = Form(None),
    cover_photo: UploadFile = File(...),
    additional_photos: List[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    
    # 1. Create Portfolio Entry
    new_portfolio = models.Portfolio(
        caterer_id=profile.id,
        booking_id=booking_id,
        title=title,
        event_type=event_type,
        description=description,
        highlights=highlights,
        location=location,
        event_date=event_date,
        visibility=visibility,
        is_featured=is_featured
    )
    db.add(new_portfolio)
    db.commit()
    db.refresh(new_portfolio)
    
    # 2. Process Cover Photo
    if cover_photo and cover_photo.filename:
        cover_url = process_and_save_image(cover_photo, is_cover=True)
        db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=cover_url, is_cover=True))
        
    # 3. Process Additional Photos (Limit to 10 for safety)
    if additional_photos:
        count = 0
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = process_and_save_image(photo, is_cover=False)
                db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=img_url, is_cover=False))
                count += 1
                
    db.commit()
    
    return {"status": "success", "message": "Portfolio created successfully!", "portfolio_id": new_portfolio.id}

@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.caterer_id == profile.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    # Delete images from disk
    for img in portfolio.images:
        try:
            filename = img.image_url.split('/')[-1]
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            # Delete thumbnail if cover
            if img.is_cover:
                thumb_path = os.path.join(THUMBNAIL_DIR, f"thumb_{filename}")
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
        except Exception as e:
            print(f"Error deleting image {img.image_url}: {e}")
            
    db.delete(portfolio)
    db.commit()
    
    return {"status": "success", "message": "Portfolio deleted successfully"}

@router.post("/{portfolio_id}/toggle-visibility")
async def toggle_portfolio_visibility(
    portfolio_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.caterer_id == profile.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    portfolio.visibility = "Hidden" if portfolio.visibility == "Public" else "Public"
    db.commit()
    
    return {"status": "success", "message": f"Portfolio is now {portfolio.visibility}", "visibility": portfolio.visibility}

@router.post("/{portfolio_id}/toggle-feature")
async def toggle_portfolio_feature(
    portfolio_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.caterer_id == profile.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    portfolio.is_featured = not portfolio.is_featured
    db.commit()
    
    return {"status": "success", "message": f"Portfolio featured status updated", "is_featured": portfolio.is_featured}

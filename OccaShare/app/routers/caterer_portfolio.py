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

def process_image_to_base64(file: UploadFile, max_size=(1920, 1080), quality=85) -> str:
    import base64
    """Compresses image to WebP and returns base64 string."""
    try:
        content = file.file.read()
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (e.g., from RGBA or P)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="WEBP", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/webp;base64,{b64}"
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
    portfolios = db.query(models.Portfolio).filter(
        models.Portfolio.caterer_id == profile.id,
        models.Portfolio.is_archived == False
    ).order_by(models.Portfolio.created_at.desc()).all()
    
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
        cover_url = process_image_to_base64(cover_photo, max_size=(1920, 1080), quality=85)
        if cover_url:
            db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=cover_url, is_cover=True))
        else:
            raise HTTPException(status_code=500, detail="Failed to process cover photo.")
        
    # 3. Process Additional Photos (Limit to 10 for safety)
    if additional_photos:
        count = 0
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = process_image_to_base64(photo, max_size=(1920, 1080), quality=85)
                if img_url:
                    db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=img_url, is_cover=False))
                    count += 1
                
    db.commit()
    
    return {"status": "success", "message": "Portfolio created successfully!", "portfolio_id": new_portfolio.id}

@router.post("/{portfolio_id}/update")
async def update_portfolio(
    portfolio_id: int,
    title: str = Form(...),
    event_type: str = Form(...),
    description: str = Form(...),
    highlights: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    event_date: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    booking_id: Optional[int] = Form(None),
    cover_photo: Optional[UploadFile] = File(None),
    additional_photos: List[UploadFile] = File(None),
    deleted_photos: Optional[str] = Form(None),
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
        
    portfolio.title = title
    portfolio.event_type = event_type
    portfolio.description = description
    portfolio.highlights = highlights
    portfolio.location = location
    portfolio.event_date = event_date
    portfolio.is_featured = is_featured
    portfolio.booking_id = booking_id
    
    if cover_photo and cover_photo.filename:
        cover_url = process_image_to_base64(cover_photo, max_size=(1920, 1080), quality=85)
        if cover_url:
            # Delete old cover photo
            old_cover = next((img for img in portfolio.images if img.is_cover), None)
            if old_cover:
                db.delete(old_cover)
            db.add(models.PortfolioImage(portfolio_id=portfolio.id, image_url=cover_url, is_cover=True))
            
    if deleted_photos:
        deleted_ids = [int(i.strip()) for i in deleted_photos.split(',') if i.strip().isdigit()]
        if deleted_ids:
            db.query(models.PortfolioImage).filter(
                models.PortfolioImage.portfolio_id == portfolio.id,
                models.PortfolioImage.id.in_(deleted_ids),
                models.PortfolioImage.is_cover == False
            ).delete(synchronize_session=False)

    if additional_photos:
        # Check how many gallery photos exist
        existing_count = db.query(models.PortfolioImage).filter(
            models.PortfolioImage.portfolio_id == portfolio.id,
            models.PortfolioImage.is_cover == False
        ).count()
        
        count = existing_count
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = process_image_to_base64(photo, max_size=(1920, 1080), quality=85)
                if img_url:
                    db.add(models.PortfolioImage(portfolio_id=portfolio.id, image_url=img_url, is_cover=False))
                    count += 1
                    
    db.commit()
    return {"status": "success", "message": "Portfolio updated successfully"}

@router.delete("/{portfolio_id}")
async def archive_portfolio(
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
        
    portfolio.is_archived = True
    db.commit()
    
    return {"status": "success", "message": "Portfolio archived successfully"}

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

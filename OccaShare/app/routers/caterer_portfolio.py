import os
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import database, models
from app.core.security import get_current_user, RoleChecker
from app.core.templates import templates
from app.services.storage import upload_file_to_cloudinary, delete_file_from_cloudinary

caterer_only = RoleChecker(["caterer"])

router = APIRouter(prefix="/caterer/portfolio", tags=["portfolio"])


async def process_image_to_cloudinary(file: UploadFile, folder: str = "gallery") -> str:
    """Uploads file to Cloudinary and returns CDN URL."""
    try:
        content = await file.read()
        url = upload_file_to_cloudinary(content, folder=folder)
        if not url:
            raise HTTPException(status_code=500, detail="Cloudinary upload returned empty URL")
        return url
    except Exception as e:
        print(f"Error processing image for Cloudinary: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file format or upload error")


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
    cover_photo: Optional[UploadFile] = File(None),
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
    
    # 2. Process Cover Photo -> Cloudinary
    if cover_photo and cover_photo.filename:
        cover_url = await process_image_to_cloudinary(cover_photo, folder="gallery")
        if cover_url:
            db.add(models.PortfolioImage(portfolio_id=new_portfolio.id, image_url=cover_url, is_cover=True))
        else:
            raise HTTPException(status_code=500, detail="Failed to process cover photo.")
        
    # 3. Process Additional Photos -> Cloudinary (Limit to 10)
    if additional_photos:
        count = 0
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = await process_image_to_cloudinary(photo, folder="gallery")
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
        cover_url = await process_image_to_cloudinary(cover_photo, folder="gallery")
        if cover_url:
            old_cover = next((img for img in portfolio.images if img.is_cover), None)
            if old_cover:
                delete_file_from_cloudinary(old_cover.image_url)
                db.delete(old_cover)
            db.add(models.PortfolioImage(portfolio_id=portfolio.id, image_url=cover_url, is_cover=True))
            
    if deleted_photos:
        deleted_ids = [int(i.strip()) for i in deleted_photos.split(',') if i.strip().isdigit()]
        if deleted_ids:
            deleted_imgs = db.query(models.PortfolioImage).filter(
                models.PortfolioImage.portfolio_id == portfolio.id,
                models.PortfolioImage.id.in_(deleted_ids),
                models.PortfolioImage.is_cover == False
            ).all()
            for d_img in deleted_imgs:
                delete_file_from_cloudinary(d_img.image_url)
                db.delete(d_img)

    if additional_photos:
        existing_count = db.query(models.PortfolioImage).filter(
            models.PortfolioImage.portfolio_id == portfolio.id,
            models.PortfolioImage.is_cover == False
        ).count()
        
        count = existing_count
        for photo in additional_photos:
            if photo.filename and count < 10:
                img_url = await process_image_to_cloudinary(photo, folder="gallery")
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

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

@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    source: str = Form(""),
    db: Session = Depends(get_db)
):
    # Validate required field
    if not name:
        raise HTTPException(status_code=400, detail="Region name is required")
    
    try:
        new_region = models.Region(
            name=name,
            capital=capital or "",
            population=population or "",
            terrain=terrain or "",
            description=description or "",
            overview=description or "",  # Overview auto-filled from description
            category=category or "",
            tags=tags or "",
            hero_image=hero_image or "",
            gallery_images=gallery_images or "",
            audio_files=audio_files or "",
            source=source or ""
        )
        
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        
        return {"success": True, "message": "Region created successfully", "region_id": new_region.id}
        
    except Exception as e:
        db.rollback()
        print(f"Error creating region: {str(e)}")  # Log error to Render logs
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

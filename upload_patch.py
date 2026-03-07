# ─── Replace the existing /api/upload/file endpoint with this ───────────────
# Also add this import at the top of main.py:
#   from storage import upload_to_supabase, delete_from_supabase

@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(""),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        size_mb = round(len(content) / (1024 * 1024), 2)
        original_name = file.filename or filename or "upload"
        content_type  = file.content_type or "application/octet-stream"

        # Upload to Supabase Storage
        public_url = await upload_to_supabase(content, original_name, content_type)

        # Save metadata to DB
        uf = models.UploadedFile(
            filename      = original_name,
            original_name = original_name,
            file_path     = public_url,   # no local path — store URL here too
            file_url      = public_url,
            file_size     = len(content),
            file_size_mb  = size_mb,
            mime_type     = content_type,
            category      = category,
            description   = description,
            is_public      = (is_public == "1"),
            region_id     = int(region_id) if region_id.isdigit() else None
        )
        db.add(uf)
        db.commit()
        db.refresh(uf)

        return {
            "success":       True,
            "url":           public_url,
            "file_size_mb":  size_mb,
            "original_name": original_name,
            "category":      category
        }
    except Exception as e:
        print(f"❌ UPLOAD ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Also replace the delete endpoint to clean up Supabase too ──────────────
@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db)):
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404)
    try:
        # Delete from Supabase Storage
        if f.file_url:
            await delete_from_supabase(f.file_url)
        db.delete(f)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

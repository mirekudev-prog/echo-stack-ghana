"""
CMS Admin API Router for EchoStack Ghana
Provides admin endpoints for managing Projects, Blocks, Audio Clips, and Revenue Plans
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import json

# Import CMS models
from cms_models import Project, ProjectBlock, AudioClip, RevenuePlan

# Import database connection
from database import get_db

router = APIRouter(prefix="/api/admin", tags=["cms-admin"])


def is_admin(request: Request) -> bool:
    """Check if the current user is an admin"""
    admin_session = request.cookies.get("admin_session")
    user_session = request.cookies.get("user_session")
    return bool(admin_session or user_session)


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/projects")
async def list_projects(request: Request, db: Session = Depends(get_db)):
    """List all CMS projects"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [{
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "status": p.status,
        "block_count": len(p.blocks),
        "created_at": str(p.created_at)
    } for p in projects]


@router.get("/projects/{project_id}")
async def get_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get a single project with all blocks"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "status": project.status,
        "blocks": [{
            "id": b.id,
            "block_type": b.block_type,
            "title": b.title,
            "content": b.content,
            "order": b.order
        } for b in sorted(project.blocks, key=lambda x: x.order)],
        "audio_clips": [{
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "duration": a.duration_seconds,
            "region": a.region
        } for a in project.audio_clips],
        "revenue_plans": [{
            "id": r.id,
            "plan_type": r.plan_type,
            "tier": r.tier,
            "name": r.name,
            "amount": r.amount,
            "currency": r.currency
        } for r in project.revenue_plans],
        "created_at": str(project.created_at)
    }


@router.post("/projects")
async def create_project(request: Request, db: Session = Depends(get_db)):
    """Create a new CMS project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    
    slug = body.get("slug", name.lower().replace(" ", "-").replace("&", "and"))
    
    project = Project(
        name=name,
        slug=slug,
        description=body.get("description", ""),
        status=body.get("status", "draft"),
        created_by="admin"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {"success": True, "id": project.id, "slug": project.slug}


@router.put("/projects/{project_id}")
async def update_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Update a project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    body = await request.json()
    
    if "name" in body:
        project.name = body["name"]
    if "description" in body:
        project.description = body["description"]
    if "status" in body:
        project.status = body["status"]
    
    db.commit()
    return {"success": True}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a project and all its blocks"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    db.delete(project)
    db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT BLOCKS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/blocks")
async def list_blocks(project_id: int, request: Request, db: Session = Depends(get_db)):
    """List all blocks for a project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    blocks = db.query(ProjectBlock).filter(
        ProjectBlock.project_id == project_id
    ).order_by(ProjectBlock.order).all()
    
    return [{
        "id": b.id,
        "block_type": b.block_type,
        "title": b.title,
        "content": b.content,
        "order": b.order
    } for b in blocks]


@router.post("/projects/{project_id}/blocks")
async def create_block(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Create a new block in a project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    body = await request.json()
    
    block = ProjectBlock(
        project_id=project_id,
        block_type=body.get("block_type", "section"),
        title=body.get("title", ""),
        content=body.get("content", ""),
        order=body.get("order", 0),
        metadata_json=json.dumps(body.get("metadata", {}))
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    
    return {"success": True, "id": block.id}


@router.put("/projects/{project_id}/blocks/{block_id}")
async def update_block(project_id: int, block_id: int, request: Request, db: Session = Depends(get_db)):
    """Update a block"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    block = db.query(ProjectBlock).filter(
        ProjectBlock.id == block_id,
        ProjectBlock.project_id == project_id
    ).first()
    if not block:
        raise HTTPException(404, "Block not found")
    
    body = await request.json()
    
    if "block_type" in body:
        block.block_type = body["block_type"]
    if "title" in body:
        block.title = body["title"]
    if "content" in body:
        block.content = body["content"]
    if "order" in body:
        block.order = body["order"]
    
    db.commit()
    return {"success": True}


@router.delete("/projects/{project_id}/blocks/{block_id}")
async def delete_block(project_id: int, block_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a block"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    block = db.query(ProjectBlock).filter(
        ProjectBlock.id == block_id,
        ProjectBlock.project_id == project_id
    ).first()
    if not block:
        raise HTTPException(404, "Block not found")
    
    db.delete(block)
    db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO CLIPS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/audio")
async def add_audio_clip(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Add an audio clip to a project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    body = await request.json()
    
    clip = AudioClip(
        project_id=project_id,
        title=body.get("title", ""),
        description=body.get("description", ""),
        url=body.get("url", ""),
        duration_seconds=body.get("duration", 0),
        region=body.get("region", ""),
        language=body.get("language", ""),
        speaker=body.get("speaker", ""),
        tags=body.get("tags", "")
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    
    return {"success": True, "id": clip.id}


# ═══════════════════════════════════════════════════════════════════════════════
# REVENUE PLANS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/revenue")
async def add_revenue_plan(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Add a revenue plan to a project"""
    if not is_admin(request):
        raise HTTPException(403, "Admin access required")
    
    body = await request.json()
    
    plan = RevenuePlan(
        project_id=project_id,
        plan_type=body.get("plan_type", "subscription"),
        tier=body.get("tier", "free"),
        name=body.get("name", ""),
        description=body.get("description", ""),
        amount=body.get("amount", 0),
        currency=body.get("currency", "GHS"),
        features=json.dumps(body.get("features", []))
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return {"success": True, "id": plan.id}

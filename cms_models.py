"""
CMS Models for EchoStack Ghana
Supports: Projects, Content Blocks, Audio Assets, Revenue Plans
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Project(Base):
    """A project in the CMS (e.g., Audio Archive & Podcast Network)"""
    __tablename__ = "cms_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="draft")  # draft, active, archived
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    blocks = relationship("ProjectBlock", back_populates="project", cascade="all, delete-orphan", order_by="ProjectBlock.order")
    audio_clips = relationship("AudioClip", back_populates="project", cascade="all, delete-orphan")
    revenue_plans = relationship("RevenuePlan", back_populates="project", cascade="all, delete-orphan")


class ProjectBlock(Base):
    """A content block within a project (sections, descriptions, instructions)"""
    __tablename__ = "cms_project_blocks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("cms_projects.id", ondelete="CASCADE"), nullable=False)
    block_type = Column(String(50), nullable=False)  # concept, section, instruction, component, detail
    title = Column(String(200), default="")
    content = Column(Text, default="")
    order = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")  # JSON for extra data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="blocks")


class AudioClip(Base):
    """Audio asset for a project (oral histories, podcasts, clips)"""
    __tablename__ = "cms_audio_clips"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("cms_projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), default="")
    description = Column(Text, default="")
    url = Column(String(500), default="")
    duration_seconds = Column(Integer, default=0)
    region = Column(String(100), default="")
    language = Column(String(100), default="")
    speaker = Column(String(200), default="")
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="audio_clips")


class RevenuePlan(Base):
    """Monetization plan for a project (subscriptions, grants, sponsorships)"""
    __tablename__ = "cms_revenue_plans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("cms_projects.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String(50), default="subscription")  # subscription, grant, sponsorship, freemium
    tier = Column(String(50), default="free")  # free, basic, premium
    name = Column(String(200), default="")
    description = Column(Text, default="")
    amount = Column(Integer, default=0)  # in smallest currency unit (pesewas)
    currency = Column(String(10), default="GHS")
    features = Column(Text, default="")  # JSON list of features
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="revenue_plans")

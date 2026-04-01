"""
Seed data for Project 9: Audio Archive & Podcast Network
Run this script to populate the CMS with the initial project data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from database import engine, get_db
from cms_models import Base, Project, ProjectBlock, AudioClip, RevenuePlan

# Create tables
Base.metadata.create_all(bind=engine)

def seed_project_nine():
    """Create Project 9: Audio Archive & Podcast Network with all blocks from the spec"""
    db = next(get_db())
    
    try:
        # Check if project already exists
        existing = db.query(Project).filter(Project.slug == "audio-archive-podcast-network").first()
        if existing:
            print(f"Project already exists with ID: {existing.id}")
            return existing.id
        
        # Create the project
        project = Project(
            name="Audio Archive & Podcast Network",
            slug="audio-archive-podcast-network",
            description="A digital platform to record, archive, and monetize oral histories, folklore, and contemporary stories from Ghana's 16 regions",
            status="active",
            created_by="admin"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        print(f"Created project: {project.name} (ID: {project.id})")
        
        # Add blocks based on the image content
        blocks = [
            # Concept block
            {
                "block_type": "concept",
                "title": "Concept",
                "content": "Create a digital platform to record, archive, and monetize oral histories, folklore, and contemporary stories from Ghana's 16 regions, preserving culture and creating content for a global African diaspora audience.",
                "order": 0
            },
            # Components & Instructions header
            {
                "block_type": "section",
                "title": "Components & Instructions",
                "content": "The project consists of four main units working together to achieve our mission of cultural preservation and audience building.",
                "order": 1
            },
            # Content Curation & Recording Unit
            {
                "block_type": "component",
                "title": "Content Curation & Recording Unit",
                "content": "Develop ethical protocols for recording elders and storytellers. Plan recording tours to specific regions (e.g., start with Greater Accra and Ashanti). Handle translations and subtitling.",
                "order": 2
            },
            # Platform & Tech Unit
            {
                "block_type": "component",
                "title": "Platform & Tech Unit",
                "content": "Build a website/app to host the archive. Design a premium subscription model for deep access and a freemium model for casual listening.",
                "order": 3
            },
            # Modern Storytelling Unit
            {
                "block_type": "component",
                "title": "Modern Storytelling Unit",
                "content": "Launch a companion podcast network featuring modern Ghanaian voices (entrepreneurs, artists, researchers) discussing how the past informs the present, attracting a younger audience.",
                "order": 4
            },
            # Integration & Pitch
            {
                "block_type": "component",
                "title": "Integration & Pitch",
                "content": "Present sample audio clips from the archive, the fully designed platform, a content calendar for the podcast network, and a revenue model combining subscriptions, grants, and sponsored series.",
                "order": 5
            },
            # Recording Tours Detail
            {
                "block_type": "detail",
                "title": "Recording Tours Plan",
                "content": """Phase 1 (Months 1-3):
• Greater Accra Region - Accra metropolitan area elders and coastal communities
• Ashanti Region - Kumasi and surrounding historic towns

Phase 2 (Months 4-6):
• Volta Region - Ewe cultural stories and traditions
• Northern Region - Dagomba, Mamprusi, and Gonja oral traditions

Phase 3 (Months 7-9):
• Central Region - Fante coastal stories
• Western Region - Nzema and Ahanta traditions

Phase 4 (Months 10-12):
• Complete coverage of remaining 10 regions""",
                "order": 6
            },
            # Ethical Protocols
            {
                "block_type": "detail",
                "title": "Ethical Recording Protocols",
                "content": """Core Principles:
1. Informed Consent - Full explanation of project scope and usage rights
2. Cultural Sensitivity - Respect for sacred/restricted stories
3. Community Benefit - Revenue sharing with source communities
4. Attribution - Proper crediting of storytellers and families
5. Revocable Rights - Storytellers can withdraw consent at any time
6. Language Preservation - Record in native languages with translations""",
                "order": 7
            },
            # Revenue Model
            {
                "block_type": "detail",
                "title": "Revenue Model",
                "content": """Revenue Streams:

1. Subscriptions (Target: 60% of revenue)
   - Free tier: Limited access to public domain recordings
   - Premium tier (GHS 29.99/month): Full archive access, exclusive content
   
2. Grants (Target: 25% of revenue)
   - UNESCO Cultural Heritage grants
   - African Union cultural preservation funds
   - Ghana Heritage Trust
   
3. Sponsored Series (Target: 15% of revenue)
   - Corporate storytelling partnerships
   - Tourism board collaborations
   - Educational institution licensing""",
                "order": 8
            },
            # Podcast Network
            {
                "block_type": "detail",
                "title": "Podcast Network Plan",
                "content": """Show Concepts:

1. "Echoes of Yesterday"
   - Traditional oral histories from elders
   - Weekly episodes, 30-45 minutes
   
2. "Ghana Rising"
   - Modern voices connecting past to present
   - Entrepreneurs, artists, researchers
   - Bi-weekly episodes, 45-60 minutes
   
3. "Soundscapes"
   - Musical traditions and cultural performances
   - Regional music spotlights
   - Weekly episodes, 30 minutes
   
4. "Language Lines"
   - Language learning through stories
   - Practical phrases and cultural context
   - Daily micro-episodes, 5-10 minutes""",
                "order": 9
            },
            # Platform Features
            {
                "block_type": "detail",
                "title": "Platform Features",
                "content": """Core Features:
• Audio player with transcription overlay
• Search by region, language, topic, or speaker
• Interactive Ghana map with regional content
• Timeline view of historical recordings
• User favorites and playlists
• Mobile-optimized progressive web app

Premium Features:
• Offline listening/download capability
• High-fidelity audio streaming
• Educational licensing and exports
• Community discussion forums
• Early access to new recordings""",
                "order": 10
            }
        ]
        
        for block_data in blocks:
            block = ProjectBlock(
                project_id=project.id,
                block_type=block_data["block_type"],
                title=block_data["title"],
                content=block_data["content"],
                order=block_data["order"]
            )
            db.add(block)
        
        # Add revenue plans
        revenue_plans = [
            {
                "plan_type": "subscription",
                "tier": "free",
                "name": "Free Access",
                "description": "Basic access to public domain recordings",
                "amount": 0,
                "currency": "GHS"
            },
            {
                "plan_type": "subscription",
                "tier": "premium",
                "name": "Premium Access",
                "description": "Full archive access, exclusive content, offline listening",
                "amount": 2999,  # GHS 29.99 in pesewas
                "currency": "GHS"
            }
        ]
        
        for plan_data in revenue_plans:
            plan = RevenuePlan(
                project_id=project.id,
                plan_type=plan_data["plan_type"],
                tier=plan_data["tier"],
                name=plan_data["name"],
                description=plan_data["description"],
                amount=plan_data["amount"],
                currency=plan_data["currency"]
            )
            db.add(plan)
        
        # Add sample audio clip
        sample_clip = AudioClip(
            project_id=project.id,
            title="Sample: Introduction to EchoStack",
            description="An introductory audio clip explaining the EchoStack mission",
            url="",
            duration_seconds=120,
            region="Greater Accra",
            language="English",
            speaker="EchoStack Team",
            tags="introduction, mission, overview"
        )
        db.add(sample_clip)
        
        db.commit()
        print(f"✅ Seeded Project 9 with {len(blocks)} blocks, {len(revenue_plans)} revenue plans, and 1 sample audio clip")
        return project.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding project: {e}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    seed_project_nine()

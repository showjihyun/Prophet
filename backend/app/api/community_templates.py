"""Community Templates CRUD endpoints.
SPEC: docs/spec/06_API_SPEC.md#community-template-endpoints
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/communities/templates", tags=["community_templates"])

# In-memory store for community templates
_community_templates: dict[str, dict] = {
    "early_adopters": {
        "template_id": "early_adopters",
        "name": "Early Adopters",
        "agent_type": "early_adopter",
        "default_size": 100,
        "description": "Tech-savvy, high openness",
        "personality_profile": {
            "openness": 0.8,
            "skepticism": 0.3,
            "trend_following": 0.7,
            "brand_loyalty": 0.4,
            "social_influence": 0.6,
        },
    },
    "general_consumers": {
        "template_id": "general_consumers",
        "name": "General Consumers",
        "agent_type": "consumer",
        "default_size": 500,
        "description": "Mainstream users",
        "personality_profile": {
            "openness": 0.5,
            "skepticism": 0.5,
            "trend_following": 0.5,
            "brand_loyalty": 0.5,
            "social_influence": 0.4,
        },
    },
    "skeptics": {
        "template_id": "skeptics",
        "name": "Skeptics",
        "agent_type": "skeptic",
        "default_size": 200,
        "description": "Critical thinkers, high skepticism",
        "personality_profile": {
            "openness": 0.3,
            "skepticism": 0.8,
            "trend_following": 0.2,
            "brand_loyalty": 0.6,
            "social_influence": 0.3,
        },
    },
    "experts": {
        "template_id": "experts",
        "name": "Industry Experts",
        "agent_type": "expert",
        "default_size": 30,
        "description": "Domain authorities",
        "personality_profile": {
            "openness": 0.6,
            "skepticism": 0.6,
            "trend_following": 0.3,
            "brand_loyalty": 0.4,
            "social_influence": 0.8,
        },
    },
    "influencers": {
        "template_id": "influencers",
        "name": "Influencers",
        "agent_type": "influencer",
        "default_size": 170,
        "description": "High reach, trend setters",
        "personality_profile": {
            "openness": 0.7,
            "skepticism": 0.3,
            "trend_following": 0.8,
            "brand_loyalty": 0.3,
            "social_influence": 0.9,
        },
    },
}


class CommunityTemplateInput(BaseModel):
    """Input schema for creating/updating a community template."""
    name: str
    agent_type: str
    default_size: int
    description: str = ""
    personality_profile: dict[str, float] = {}


@router.get("/")
async def list_templates() -> dict:
    """List all community templates.
    SPEC: docs/spec/06_API_SPEC.md#community-template-endpoints
    """
    return {"templates": list(_community_templates.values())}


@router.post("/")
async def create_template(body: CommunityTemplateInput) -> dict:
    """Create a new community template.
    SPEC: docs/spec/06_API_SPEC.md#community-template-endpoints
    """
    template_id = str(uuid.uuid4())
    template = {
        "template_id": template_id,
        "name": body.name,
        "agent_type": body.agent_type,
        "default_size": body.default_size,
        "description": body.description,
        "personality_profile": body.personality_profile,
    }
    _community_templates[template_id] = template
    return template


@router.put("/{template_id}")
async def update_template(template_id: str, body: CommunityTemplateInput) -> dict:
    """Update an existing community template.
    SPEC: docs/spec/06_API_SPEC.md#community-template-endpoints
    """
    if template_id not in _community_templates:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    updated = {
        "template_id": template_id,
        "name": body.name,
        "agent_type": body.agent_type,
        "default_size": body.default_size,
        "description": body.description,
        "personality_profile": body.personality_profile,
    }
    _community_templates[template_id] = updated
    return updated


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: str) -> None:
    """Delete a community template.
    SPEC: docs/spec/06_API_SPEC.md#community-template-endpoints
    """
    if template_id not in _community_templates:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    del _community_templates[template_id]


__all__ = ["router"]

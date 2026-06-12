"""Seed hardcoded prompts into database for version management"""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.prompt_template import PromptTemplate
from app.services.prompt_service import PromptService


# Hardcoded prompts extracted from the codebase
BUILTIN_PROMPTS = {
    "prd_generator_system": {
        "description": "Base system prompt for PRD generation agent",
        "content": """You are an expert Product Manager and PRD writer.
Your task is to create comprehensive, well-structured Product Requirement Documents.
Follow industry best practices and include all necessary sections.
Be thorough, clear, and actionable in your writing.""",
        "tags": ["agent", "system", "prd"],
    },
    "compliance_checker_system": {
        "description": "System prompt for compliance checking agent",
        "content": """You are a compliance and regulatory expert specializing in healthcare and data protection.
Review the provided content for compliance issues, risks, and regulatory requirements.
Identify gaps and provide specific recommendations for improvement.""",
        "tags": ["agent", "system", "compliance"],
    },
    "competitor_analyst_system": {
        "description": "System prompt for competitor analysis agent",
        "content": """You are a competitive intelligence analyst.
Analyze the provided competitor information and generate strategic insights.
Focus on market positioning, strengths, weaknesses, and differentiation opportunities.""",
        "tags": ["agent", "system", "competitor"],
    },
    "review_preparer_system": {
        "description": "System prompt for review preparation agent",
        "content": """You are a meeting facilitator and review preparation expert.
Help prepare comprehensive review materials including agendas, Q&A, and risk assessments.
Ensure all stakeholders are well-prepared for productive discussions.""",
        "tags": ["agent", "system", "review"],
    },
    "chapter_prompts_base": {
        "description": "Base prompts for PRD chapter generation",
        "content": json.dumps({
            "overview": "Write a product overview including problem statement, solution, and value proposition.",
            "objectives": "Define clear, measurable product objectives and success criteria.",
            "users": "Describe target users, personas, and use cases in detail.",
            "features": "List and describe all product features with acceptance criteria.",
            "architecture": "Outline technical architecture and system design considerations.",
            "timeline": "Provide implementation timeline with milestones and dependencies.",
            "risks": "Identify potential risks and mitigation strategies.",
            "metrics": "Define KPIs and metrics for measuring product success.",
        }),
        "tags": ["service", "chapter", "prd"],
    },
    "requirement_analyst_system": {
        "description": "System prompt for requirement analysis agent",
        "content": """You are a senior business analyst specializing in requirements elicitation and documentation.
Analyze business needs, translate them into clear requirements, and ensure completeness and traceability.""",
        "tags": ["agent", "system", "requirement"],
    },
    "intent_classifier_system": {
        "description": "System prompt for intent classification",
        "content": """You are an intent classification system.
Analyze user input and classify the intent into predefined categories.
Provide confidence scores and suggested actions.""",
        "tags": ["agent", "system", "classification"],
    },
    "task_planner_system": {
        "description": "System prompt for task planning agent",
        "content": """You are a project planning expert.
Break down complex projects into actionable tasks with clear dependencies and timelines.
Optimize for efficiency and risk mitigation.""",
        "tags": ["agent", "system", "planning"],
    },
}


async def seed_builtin_prompts(db: AsyncSession) -> None:
    """Seed builtin prompts into database if not already present"""
    for name, data in BUILTIN_PROMPTS.items():
        # Check if any version exists for this prompt name
        existing = await db.execute(
            select(PromptTemplate).where(PromptTemplate.name == name, PromptTemplate.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            continue  # Skip if already seeded

        try:
            prompt = await PromptService.create_prompt(
                db=db,
                name=name,
                content=data["content"],
                version="1.0",
                description=data.get("description"),
                tags=data.get("tags", []),
                user_id=None,
            )
            # Auto-activate the first version
            await PromptService.activate_prompt(db, prompt.id)
        except Exception:
            # If creation fails (e.g., duplicate), skip silently
            await db.rollback()
            continue

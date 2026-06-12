"""Prompt resolver for runtime prompt retrieval from database"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.models.prompt_template import PromptTemplate


async def get_active_prompt(db: AsyncSession, name: str, default: Optional[str] = None) -> str:
    """Get the currently active prompt for a given name.

    Falls back to hardcoded default if no active prompt found in DB.
    This enables gradual migration from hardcoded to DB-managed prompts.
    """
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.is_active == True,
            PromptTemplate.deleted_at.is_(None),
        )
    )
    prompt = result.scalar_one_or_none()
    if prompt:
        return prompt.content
    return default or ""


async def get_prompt_with_fallback(
    db: AsyncSession,
    name: str,
    fallback_content: str,
) -> str:
    """Get active prompt from DB, or return fallback content if not found.

    Usage in agents/services:
        prompt = await get_prompt_with_fallback(
            db, "prd_generator_system", self.BASE_SYSTEM_PROMPT
        )
    """
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.is_active == True,
            PromptTemplate.deleted_at.is_(None),
        )
    )
    prompt = result.scalar_one_or_none()
    if prompt:
        return prompt.content
    return fallback_content

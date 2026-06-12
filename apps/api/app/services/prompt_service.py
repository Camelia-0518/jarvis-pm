"""Prompt template service layer"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List

from app.models.prompt_template import PromptTemplate
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError


class PromptService:
    """Service for prompt template CRUD and version management"""

    @staticmethod
    async def create_prompt(
        db: AsyncSession,
        name: str,
        content: str,
        version: str = "1.0",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> PromptTemplate:
        """Create a new prompt version"""
        # Check for duplicate name+version
        existing = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.version == version,
                PromptTemplate.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                message=f"Prompt '{name}' version '{version}' already exists"
            )

        prompt = PromptTemplate(
            name=name,
            description=description,
            content=content,
            version=version,
            is_active=False,  # Don't auto-activate; require explicit activation
            tags=tags or [],
            created_by=user_id,
        )
        db.add(prompt)
        await db.commit()
        await db.refresh(prompt)
        return prompt

    @staticmethod
    async def activate_prompt(db: AsyncSession, prompt_id: str) -> PromptTemplate:
        """Activate a prompt version and deactivate others with the same name"""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.deleted_at.is_(None))
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise ResourceNotFoundError("PromptTemplate", prompt_id)

        # Deactivate all other versions of the same name
        await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.name == prompt.name,
                PromptTemplate.id != prompt_id,
                PromptTemplate.is_active == True,
                PromptTemplate.deleted_at.is_(None),
            )
        )
        # Use update statement for batch deactivation
        from sqlalchemy import update
        await db.execute(
            update(PromptTemplate)
            .where(
                PromptTemplate.name == prompt.name,
                PromptTemplate.id != prompt_id,
            )
            .values(is_active=False)
        )

        prompt.is_active = True
        await db.commit()
        await db.refresh(prompt)
        return prompt

    @staticmethod
    async def get_active_prompt(db: AsyncSession, name: str) -> Optional[PromptTemplate]:
        """Get the currently active prompt for a given name"""
        result = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.is_active == True,
                PromptTemplate.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_prompt_by_id(db: AsyncSession, prompt_id: str) -> Optional[PromptTemplate]:
        """Get prompt by ID"""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_prompts(
        db: AsyncSession,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> tuple[List[PromptTemplate], int]:
        """List prompts with filtering and pagination. When user_id provided, scope to that user."""
        query = select(PromptTemplate).where(PromptTemplate.deleted_at.is_(None))
        if user_id:
            query = query.where(PromptTemplate.created_by == user_id)

        if name:
            query = query.where(PromptTemplate.name == name)
        if is_active is not None:
            query = query.where(PromptTemplate.is_active == is_active)
        if tag:
            # JSON contains query for tags
            query = query.where(PromptTemplate.tags.contains([tag]))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(PromptTemplate.created_at))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        prompts = result.scalars().all()
        return list(prompts), total

    @staticmethod
    async def list_versions(db: AsyncSession, name: str) -> List[PromptTemplate]:
        """List all versions for a given prompt name"""
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name, PromptTemplate.deleted_at.is_(None))
            .order_by(desc(PromptTemplate.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_prompt(
        db: AsyncSession,
        prompt_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        """Update mutable fields of a prompt (content is immutable after creation)"""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.deleted_at.is_(None))
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise ResourceNotFoundError("PromptTemplate", prompt_id)

        if description is not None:
            prompt.description = description
        if tags is not None:
            prompt.tags = tags

        await db.commit()
        await db.refresh(prompt)
        return prompt

    @staticmethod
    async def delete_prompt(db: AsyncSession, prompt_id: str) -> None:
        """Delete a prompt version. Cannot delete if it's the only active version."""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id, PromptTemplate.deleted_at.is_(None))
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise ResourceNotFoundError("PromptTemplate", prompt_id)

        # Check if this is the only non-deleted version for this name
        versions_result = await db.execute(
            select(func.count(PromptTemplate.id)).where(
                PromptTemplate.name == prompt.name,
                PromptTemplate.deleted_at.is_(None),
            )
        )
        version_count = versions_result.scalar()

        if prompt.is_active and version_count == 1:
            raise ResourceConflictError(
                message="Cannot delete the only version of a prompt. Create another version first."
            )

        prompt.soft_delete()
        await db.commit()

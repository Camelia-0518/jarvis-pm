"""Shared CRUD helpers — eliminate repeated ownership-verify / query / update patterns.

委托到 app.core.permissions 统一权限层，保持向后兼容。
"""

from typing import Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from pydantic import BaseModel

from app.core.database import Base
from app.core.permissions import (
    require_project_owner,
    require_resource_via_project,
)
from app.core.exceptions import AppException


async def verify_project_owner(db: AsyncSession, project_id: str, user_id: str):
    """Verify project exists and belongs to user. Raises 404 if not.

    Deprecated: 直接使用 app.core.permissions.require_project_owner
    """
    return await require_project_owner(db, project_id, user_id)


async def get_owned_resource(
    db: AsyncSession,
    model: Type[Base],
    resource_id: str,
    user_id: str,
    *,
    join_project: bool = True,
) -> Any:
    """Fetch a resource by id, verifying ownership via Project join. Raises 404 if not found.

    Deprecated: 直接使用 app.core.permissions.require_resource_via_project
    """
    if join_project:
        return await require_resource_via_project(db, model, resource_id, user_id)
    # 无 project join 的直接归属校验暂不在此路径统一
    query = select(model).where(model.id == resource_id, model.deleted_at.is_(None))
    result = await db.execute(query)
    resource = result.scalar_one_or_none()
    if not resource:
        raise AppException(f"{model.__name__} not found", code="NOT_FOUND", status_code=404)
    return resource


async def list_project_resources(
    db: AsyncSession,
    model: Type[Base],
    project_id: str,
    user_id: str,
    response_schema: Type[BaseModel],
    *,
    sort_by: str | None = None,
    sort_order: str = "desc",
):
    """List resources for a project, with ownership check. Returns (items, schema)."""
    await require_project_owner(db, project_id, user_id)
    sort_col = getattr(model, sort_by) if sort_by else model.created_at
    order_fn = desc if sort_order == "desc" else asc
    result = await db.execute(
        select(model)
        .where(model.project_id == project_id, model.deleted_at.is_(None))
        .order_by(order_fn(sort_col))
    )
    items = result.scalars().all()
    return items, response_schema


async def apply_update(db: AsyncSession, instance: Any, update_data: BaseModel) -> None:
    """Apply Pydantic update data to a model instance and commit."""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)
    await db.commit()
    await db.refresh(instance)

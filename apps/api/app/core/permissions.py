"""统一资源归属校验层

消除散落在各 endpoint 里的手写 created_by 检查，提供三种标准模式：

    Pattern A — 直接归属:        Resource.created_by == user_id
    Pattern B — 项目级归属:      Project.created_by == user_id (验证项目归属后信任项目下的子资源)
    Pattern C — 通过 Project Join: Resource JOIN Project WHERE Project.created_by == user_id

用法:
    from app.core.permissions import require_project_owner, require_resource_owner

    # Pattern A: 验证资源直接归属
    prd = await require_resource_owner(db, PRD, prd_id, user_id)

    # Pattern B: 验证项目归属
    project = await require_project_owner(db, project_id, user_id)

    # Pattern C: 通过项目验证子资源归属
    annotation = await require_resource_via_project(db, PRDAnnotation, annotation_id, user_id)
"""

from typing import Any, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.exceptions import AppException
from app.models.project import Project


# =============================================================================
# Pattern A — 直接归属校验 (Resource.created_by == user_id)
# =============================================================================

async def require_resource_owner(
    db: AsyncSession,
    model: Type[Base],
    resource_id: str,
    user_id: str,
    *,
    error_message: str | None = None,
) -> Any:
    """验证资源存在且属于当前用户，返回资源对象。

    适用于: PRD, Template, Battle, Feedback, PRDComment 等带 created_by 列的模型。

    Raises:
        AppException(404): 资源不存在或不属于当前用户
    """
    query = select(model).where(
        model.id == resource_id,
        model.created_by == user_id,
    )
    # 如果模型有软删除，排除已删除记录
    if hasattr(model, "deleted_at"):
        query = query.where(model.deleted_at.is_(None))

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        name = error_message or f"{model.__name__} not found"
        raise AppException(name, code="NOT_FOUND", status_code=404)

    return resource


# =============================================================================
# Pattern B — 项目级归属校验 (Project.created_by == user_id)
# =============================================================================

async def require_project_owner(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    *,
    error_message: str | None = None,
) -> Project:
    """验证项目存在且属于当前用户，返回 Project 对象。

    适用于: 需要先验证项目归属，再操作项目下的子资源（PRD、Annotation 等）。

    Raises:
        AppException(404): 项目不存在或不属于当前用户
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise AppException(
            error_message or "Project not found",
            code="NOT_FOUND",
            status_code=404,
        )

    return project


# =============================================================================
# Pattern C — 通过 Project Join 校验子资源归属
# =============================================================================

async def require_resource_via_project(
    db: AsyncSession,
    model: Type[Base],
    resource_id: str,
    user_id: str,
    *,
    error_message: str | None = None,
) -> Any:
    """通过 Project join 验证子资源归属，返回资源对象。

    适用于: 有 project_id 外键但不直接有 created_by 的模型，
    或其 created_by 语义不等于归属（如 Persona、Requirement、Competitor 等）。

    Raises:
        AppException(404): 资源不存在、项目不存在或项目不属于当前用户
    """
    query = (
        select(model)
        .join(Project, model.project_id == Project.id)
        .where(
            model.id == resource_id,
            Project.created_by == user_id,
        )
    )
    if hasattr(model, "deleted_at"):
        query = query.where(model.deleted_at.is_(None))

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        name = error_message or f"{model.__name__} not found"
        raise AppException(name, code="NOT_FOUND", status_code=404)

    return resource


# =============================================================================
# 便捷：PRD 归属校验（常用组合）
# =============================================================================

async def require_prd_owner(
    db: AsyncSession,
    prd_id: str,
    user_id: str,
) -> Any:
    """验证 PRD 存在且属于当前用户，返回 PRD 对象。

    等价于 require_resource_owner(db, PRD, prd_id, user_id)，
    但提供更清晰的语义命名，无需调用方导入 PRD 模型。
    """
    from app.models.prd import PRD

    return await require_resource_owner(db, PRD, prd_id, user_id)

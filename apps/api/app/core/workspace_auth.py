"""Workspace 角色权限层

在统一权限层（permissions.py）之上，增加 workspace 级别的角色校验。

用法:
    from app.core.workspace_auth import require_workspace_role, get_current_workspace

    @router.get("/...")
    async def endpoint(
        workspace_id: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ):
        membership = await require_workspace_role(db, workspace_id, user_id, WorkspaceRole.EDITOR)
        # membership.role >= EDITOR
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.workspace import Membership, WorkspaceRole, ROLE_HIERARCHY, can_manage_members


async def get_current_workspace(
    db: AsyncSession,
    user_id: str,
) -> Optional[str]:
    """获取用户当前活跃的 workspace_id。

    返回第一个活跃 membership 对应的 workspace，或 None。
    """
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.is_active == True,  # noqa: E712
        ).limit(1)
    )
    m = result.scalar_one_or_none()
    return m.workspace_id if m else None


async def require_workspace_role(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    min_role: WorkspaceRole,
) -> Membership:
    """验证用户在 workspace 中的角色不低于 min_role。

    Raises:
        AppException(403): 无权访问或角色不足
        AppException(404): workspace 不存在或用户不是成员
    """
    result = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
            Membership.is_active == True,  # noqa: E712
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AppException(
            "无权限访问此工作区",
            code="WORKSPACE_ACCESS_DENIED",
            status_code=403,
        )

    if ROLE_HIERARCHY.get(membership.role, 0) < ROLE_HIERARCHY.get(min_role, 0):
        raise AppException(
            f"需要 {min_role.value} 或更高权限",
            code="INSUFFICIENT_ROLE",
            status_code=403,
        )

    return membership


async def require_workspace_admin(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> Membership:
    """验证用户是 workspace admin 或 owner。"""
    return await require_workspace_role(db, workspace_id, user_id, WorkspaceRole.ADMIN)


async def list_user_workspaces(
    db: AsyncSession,
    user_id: str,
) -> list[dict]:
    """列出用户所属的所有 workspace 及角色。"""
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.is_active == True,  # noqa: E712
        )
    )
    memberships = result.scalars().all()

    workspace_ids = [m.workspace_id for m in memberships]
    if not workspace_ids:
        return []

    from app.models.workspace import Workspace
    ws_result = await db.execute(
        select(Workspace).where(Workspace.id.in_(workspace_ids))
    )
    workspaces = {w.id: w for w in ws_result.scalars().all()}

    return [
        {
            "workspace_id": m.workspace_id,
            "name": workspaces[m.workspace_id].name if m.workspace_id in workspaces else "Unknown",
            "slug": workspaces[m.workspace_id].slug if m.workspace_id in workspaces else "",
            "role": m.role.value if m.role else None,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in memberships
    ]

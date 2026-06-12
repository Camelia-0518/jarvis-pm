"""Workspace + Membership API"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.exceptions import AppException
from app.core.workspace_auth import (
    require_workspace_role,
    require_workspace_admin,
    list_user_workspaces,
)
from app.models.workspace import Workspace, Membership, WorkspaceRole
from app.models.audit_log import AuditLog

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None


class MemberUpdate(BaseModel):
    user_id: str
    role: str = Field(..., pattern="^(admin|editor|viewer)$")


# ── Workspace CRUD ──


@router.get("/workspaces", response_model=dict)
async def list_workspaces(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户所属的所有 workspace"""
    ws_list = await list_user_workspaces(db, user_id)
    return ResponseBuilder.success(ws_list)


@router.post("/workspaces", response_model=dict, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建 workspace 并自动成为 owner"""
    # Check slug uniqueness
    existing = await db.execute(select(Workspace).where(Workspace.slug == data.slug))
    if existing.scalar_one_or_none():
        raise AppException("slug 已被使用", code="DUPLICATE_SLUG", status_code=409)

    ws = Workspace(
        id=str(uuid.uuid4()),
        name=data.name,
        slug=data.slug,
        description=data.description,
    )
    db.add(ws)
    await db.flush()

    # Auto-join as owner
    membership = Membership(
        workspace_id=ws.id,
        user_id=user_id,
        role=WorkspaceRole.OWNER,
        joined_at=ws.created_at,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(ws)

    # Audit log
    db.add(AuditLog(
        user_id=user_id,
        workspace_id=ws.id,
        action="create",
        resource_type="workspace",
        resource_id=ws.id,
        summary=f"创建了工作区 {ws.name}",
    ))
    await db.commit()

    return ResponseBuilder.created({
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "role": "owner",
    })


# ── Members ──


@router.get("/workspaces/{workspace_id}/members", response_model=dict)
async def list_members(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """列出 workspace 成员（需 admin+）"""
    await require_workspace_admin(db, workspace_id, user_id)

    result = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.is_active == True,  # noqa: E712
        )
    )
    members = result.scalars().all()

    # Resolve user emails
    from app.models.user import User
    user_ids = [m.user_id for m in members]
    user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map = {u.id: u for u in user_result.scalars().all()}

    return ResponseBuilder.success([
        {
            "user_id": m.user_id,
            "email": user_map[m.user_id].email if m.user_id in user_map else "",
            "name": user_map[m.user_id].name if m.user_id in user_map else "",
            "role": m.role.value if m.role else None,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in members
    ])


@router.put("/workspaces/{workspace_id}/members/{target_user_id}", response_model=dict)
async def update_member_role(
    workspace_id: str,
    target_user_id: str,
    data: MemberUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新成员角色（需 admin+，不能修改 owner）"""
    await require_workspace_admin(db, workspace_id, user_id)

    result = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == target_user_id,
            Membership.is_active == True,  # noqa: E712
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise AppException("成员不存在", code="NOT_FOUND", status_code=404)
    if m.role == WorkspaceRole.OWNER:
        raise AppException("不能修改 owner 的角色", code="CANNOT_MODIFY_OWNER", status_code=400)

    old_role = m.role.value
    m.role = WorkspaceRole(data.role)
    await db.commit()

    db.add(AuditLog(
        user_id=user_id, workspace_id=workspace_id, action="update",
        resource_type="workspace", resource_id=workspace_id,
        summary=f"将成员 {target_user_id} 角色从 {old_role} 改为 {data.role}",
    ))
    await db.commit()

    return ResponseBuilder.success({"message": f"角色已更新为 {data.role}"})


# ── Invite ──


class InviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    role: str = Field(default="editor", pattern="^(admin|editor|viewer)$")


@router.post("/workspaces/{workspace_id}/invite", response_model=dict)
async def invite_member(
    workspace_id: str,
    data: InviteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """邀请用户加入 workspace（需 admin+）。

    在真实环境中会发邮件。当前版本：如果用户已存在，直接添加为成员。
    """
    await require_workspace_admin(db, workspace_id, user_id)

    from app.models.user import User
    from datetime import datetime, timezone

    # Look up user by email
    user_result = await db.execute(select(User).where(User.email == data.email))
    invited_user = user_result.scalar_one_or_none()

    if not invited_user:
        raise AppException(
            "用户不存在。请先注册账号后再邀请。",
            code="USER_NOT_FOUND",
            status_code=404,
        )

    # Check existing membership
    existing = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == invited_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException("用户已是该工作区成员", code="ALREADY_MEMBER", status_code=409)

    m = Membership(
        workspace_id=workspace_id,
        user_id=invited_user.id,
        role=WorkspaceRole(data.role),
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc),
    )
    db.add(m)
    await db.commit()

    db.add(AuditLog(
        user_id=user_id, workspace_id=workspace_id, action="create",
        resource_type="workspace", resource_id=workspace_id,
        summary=f"邀请了 {invited_user.email} 加入工作区 (角色: {data.role})",
    ))
    await db.commit()

    return ResponseBuilder.success({
        "message": f"已邀请 {invited_user.email} 加入工作区",
        "user_id": invited_user.id,
        "role": data.role,
    })

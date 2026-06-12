"""Workspace + Membership — 多租户协作地基

替代 created_by 单用户隔离，升级为团队级资源归属。
"""

import enum

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean

from app.core.database import Base
from app.models.mixins import TimestampMixin


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"       # 创建者，不可移除，唯一
    ADMIN = "admin"       # 管理员，可管理成员/模板/提示词
    EDITOR = "editor"     # 编辑者，可创建/修改 PRD/项目
    VIEWER = "viewer"     # 只读，不可修改任何资源


# 角色权限层级（数字越大权限越高）
ROLE_HIERARCHY = {
    WorkspaceRole.VIEWER: 0,
    WorkspaceRole.EDITOR: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}


def can_manage_members(role: WorkspaceRole) -> bool:
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY[WorkspaceRole.ADMIN]


def can_edit_content(role: WorkspaceRole) -> bool:
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY[WorkspaceRole.EDITOR]


class Workspace(Base, TimestampMixin):
    """工作区 — 团队协作的顶层容器"""

    __tablename__ = "workspaces"

    name = Column(String(200), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    settings = Column(Text, nullable=True)  # JSON string, workspace-level config

    # 从旧单用户模式迁移的标记
    migrated_from_user_id = Column(String, ForeignKey("users.id"), nullable=True)


class Membership(Base, TimestampMixin):
    """成员关系 — 用户在工作区中的角色"""

    __tablename__ = "memberships"

    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(Enum(WorkspaceRole), nullable=False, default=WorkspaceRole.EDITOR)
    is_active = Column(Boolean, default=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)

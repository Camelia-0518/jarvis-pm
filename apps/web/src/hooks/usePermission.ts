"use client";

import { useWorkspaceStore } from "@/stores/workspaceStore";

type Role = "owner" | "admin" | "editor" | "viewer";

const ROLE_LEVEL: Record<Role, number> = {
  owner: 4,
  admin: 3,
  editor: 2,
  viewer: 1,
};

/** Check if the active workspace role meets the minimum requirement */
export function usePermission(minRole: Role): boolean {
  const activeRole = useWorkspaceStore((s) => s.activeRole);
  if (!activeRole) return minRole === "viewer"; // no workspace = public, viewer-only
  const currentLevel = ROLE_LEVEL[activeRole as Role] ?? 0;
  const requiredLevel = ROLE_LEVEL[minRole];
  return currentLevel >= requiredLevel;
}

/** Admin+ can manage members */
export function useCanManageMembers(): boolean {
  return usePermission("admin");
}

/** Editor+ can edit content */
export function useCanEditContent(): boolean {
  return usePermission("editor");
}

/** Pure function versions (for non-hook contexts) */
export function canManageMembers(role: string | null): boolean {
  const level = ROLE_LEVEL[role as Role] ?? 0;
  return level >= ROLE_LEVEL["admin"];
}

export function canEditContent(role: string | null): boolean {
  const level = ROLE_LEVEL[role as Role] ?? 0;
  return level >= ROLE_LEVEL["editor"];
}

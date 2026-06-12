"use client";

import { create } from "zustand";
import { workspaceApi, type WorkspaceInfo } from "@/lib/api";

export type { WorkspaceInfo };

interface WorkspaceState {
  workspaces: WorkspaceInfo[];
  activeWorkspaceId: string | null;
  activeRole: string | null;
  isLoading: boolean;
  fetchWorkspaces: () => Promise<void>;
  setActiveWorkspace: (id: string, role: string) => void;
  clearActiveWorkspace: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>()((set, get) => ({
  workspaces: [],
  activeWorkspaceId: typeof window !== "undefined" ? localStorage.getItem("activeWorkspaceId") : null,
  activeRole: typeof window !== "undefined" ? localStorage.getItem("activeRole") : null,
  isLoading: false,

  fetchWorkspaces: async () => {
    set({ isLoading: true });
    try {
      const list = await workspaceApi.list();
      const { activeWorkspaceId } = get();
      if (list.length && !activeWorkspaceId) {
        const first = list[0];
        set({
          workspaces: list,
          activeWorkspaceId: first.workspace_id,
          activeRole: first.role,
          isLoading: false,
        });
        localStorage.setItem("activeWorkspaceId", first.workspace_id);
        localStorage.setItem("activeRole", first.role);
      } else {
        const stillMember = list.find(
          (w) => w.workspace_id === activeWorkspaceId
        );
        if (!stillMember && list.length) {
          const first = list[0];
          set({
            workspaces: list,
            activeWorkspaceId: first.workspace_id,
            activeRole: first.role,
            isLoading: false,
          });
          localStorage.setItem("activeWorkspaceId", first.workspace_id);
          localStorage.setItem("activeRole", first.role);
        } else {
          set({ workspaces: list, isLoading: false });
        }
      }
    } catch {
      set({ isLoading: false });
    }
  },

  setActiveWorkspace: (id, role) => {
    localStorage.setItem("activeWorkspaceId", id);
    localStorage.setItem("activeRole", role);
    set({ activeWorkspaceId: id, activeRole: role });
  },

  clearActiveWorkspace: () => {
    localStorage.removeItem("activeWorkspaceId");
    localStorage.removeItem("activeRole");
    set({ activeWorkspaceId: null, activeRole: null });
  },
}));

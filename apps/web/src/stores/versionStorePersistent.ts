// 版本控制状态管理（持久化版）

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Version {
  id: string;
  documentId?: string;
  projectId?: string;
  versionNumber: number;
  message: string;
  content: string;
  diff?: {
    added: number;
    removed: number;
    lines: Array<{ type: 'added' | 'removed' | 'context'; content: string }>;
  };
  author: {
    id: string;
    name: string;
  };
  branch: string;
  branchId?: string;
  createdAt: string;
}

export interface Branch {
  id: string;
  name: string;
  documentId?: string;
  projectId?: string;
  baseBranch?: string;
  isDefault: boolean;
  createdAt: string;
}

interface VersionState {
  versions: Version[];
  branches: Branch[];
  currentBranch: string | null;

  // Actions
  setVersions: (versions: Version[]) => void;
  addVersion: (version: Version) => void;
  setBranches: (branches: Branch[]) => void;
  createBranch: (branch: Branch) => void;
  switchBranch: (branchId: string) => void;
  getVersionsByBranch: (branchId: string) => Version[];
  getVersionById: (id: string) => Version | undefined;
}

export const useVersionStorePersistent = create<VersionState>()(
  persist(
    (set, get) => ({
      versions: [],
      branches: [],
      currentBranch: 'main',

      setVersions: (versions) => set({ versions }),

      addVersion: (version) =>
        set((state) => ({
          versions: [version, ...state.versions],
        })),

      setBranches: (branches) => set({ branches }),

      createBranch: (branch) =>
        set((state) => ({
          branches: [...state.branches, branch],
        })),

      switchBranch: (branchId) => set({ currentBranch: branchId }),

      getVersionsByBranch: (branchId) => {
        return get().versions.filter((v) => v.branch === branchId);
      },

      getVersionById: (id) => {
        return get().versions.find((v) => v.id === id);
      },
    }),
    {
      name: 'aipm-versions',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

export default useVersionStorePersistent;

import { create } from 'zustand'
import type { Version, VersionBranch as Branch } from '@/types/version'

interface VersionState {
  versions: Version[]
  branches: Branch[]
  currentBranch: string

  // Actions
  addVersion: (version: Omit<Version, 'id' | 'createdAt'>) => void
  switchBranch: (branchName: string) => void
  createBranch: (branch: Omit<Branch, 'id' | 'createdAt'>) => void
  restoreVersion: (versionId: string) => void
  compareVersions: (v1: string, v2: string) => { additions: number; deletions: number }
}

export const useVersionStore = create<VersionState>((set, get) => ({
  versions: [],
  branches: [],
  currentBranch: 'main',

  addVersion: (version) => {
    const newVersion: Version = {
      ...version,
      id: `v${Date.now()}`,
      createdAt: new Date(),
    }
    set((state) => ({
      versions: [...state.versions, newVersion],
    }))
  },

  switchBranch: (branchName) => {
    set({ currentBranch: branchName })
  },

  createBranch: (branch) => {
    const newBranch: Branch = {
      ...branch,
      id: `b${Date.now()}`,
      createdAt: new Date(),
    }
    set((state) => ({
      branches: [...state.branches, newBranch],
    }))
  },

  restoreVersion: (versionId) => {
    const version = get().versions.find((v) => v.id === versionId)
    if (version) {
      // Version restoration logic placeholder
    }
  },

  compareVersions: (v1, v2) => {
    const version1 = get().versions.find((v) => v.id === v1)
    const version2 = get().versions.find((v) => v.id === v2)

    if (!version1?.diff || !version2?.diff) {
      return { additions: 0, deletions: 0 }
    }

    return {
      additions: version2.diff.added - version1.diff.added,
      deletions: version2.diff.removed - version1.diff.removed,
    }
  },
}))

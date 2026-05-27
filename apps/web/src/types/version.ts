export interface Version {
  id: string;
  documentId: string;
  documentType: 'prd' | 'design' | 'code' | 'architecture';
  versionNumber: number;
  message: string;
  content: string;
  diff?: VersionDiff;
  author: {
    type: 'user' | 'agent';
    id: string;
    name: string;
  };
  createdAt: Date;
  parentVersion?: string;
  // 关联版本 - 解决 PRD v3 对应 Design v2 对应 Code v5 的断层问题
  linkedVersions?: {
    prd?: string;
    design?: string;
    code?: string;
    architecture?: string;
  };
  // 受影响的其他文档
  affectedDocuments?: {
    documentId: string;
    documentType: 'prd' | 'design' | 'code' | 'architecture';
    impact: 'major' | 'minor' | 'none';
    description: string;
  }[];
}

// 统一时间线事件
export interface TimelineEvent {
  id: string;
  timestamp: Date;
  type: 'version' | 'comment' | 'agent_action' | 'conflict' | 'merge';
  title: string;
  description: string;
  actor: {
    type: 'user' | 'agent';
    name: string;
    avatar?: string;
  };
  metadata?: {
    versionId?: string;
    documentType?: string;
    relatedDocuments?: string[];
  };
}

export interface VersionDiff {
  added: number;
  removed: number;
  modified: number;
  hunks: DiffHunk[];
}

export interface DiffHunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: DiffLine[];
}

export interface DiffLine {
  type: 'added' | 'removed' | 'context';
  content: string;
  lineNumber: number;
}

export interface DocumentVersionHistory {
  documentId: string;
  currentVersion: number;
  versions: Version[];
  branches: VersionBranch[];
}

export interface VersionBranch {
  id: string;
  name: string;
  baseVersion: string;
  headVersion: string;
  createdAt: Date;
}

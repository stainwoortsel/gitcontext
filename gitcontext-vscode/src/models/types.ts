export interface OTALog {
  id: string;
  thought: string;
  action: string;
  result: string;
  timestamp: string;
  filesAffected: string[];
}

export interface ContextCommit {
  id: string;
  message: string;
  timestamp: string;
  parent?: string;
  decisions: string[];
  alternatives: Array<{what: string; whyRejected: string}>;
  otaLogs: OTALog[];
  filesSnapshot: Record<string, string>;
  metadata: Record<string, any>;
}

export interface SquashResult {
  decisions: string[];
  rejectedAlternatives: Array<{what: string; whyRejected: string}>;
  keyInsights: string[];
  architectureSummary: string;
  otaCount: number;
  originalCommits: number;
  branchName: string;
  mergedAt: string;
}

export interface BranchInfo {
  name: string;
  created: string;
  lastModified: string;
  currentCommit: string | null;
  commits: string[];
  parent?: string;
  isCurrent: boolean;
  metadata: Record<string, any>;
}

export interface StatusInfo {
  currentBranch: string;
  commits: number;
  latestCommit?: string;
  latestCommitId?: string;
  uncommittedChanges: boolean;
  allBranches: string[];
}

export type TreeItemType = 'branch' | 'current-branch' | 'commit' | 'ota' | 'folder' | 'file';

export interface TreeItemData {
  type: TreeItemType;
  branch?: string;
  commitId?: string;
  logId?: string;
  path?: string;
}
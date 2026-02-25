import * as vscode from 'vscode';
import { exec } from 'child-process-promise';
import * as fs from 'fs-extra';
import * as path from 'path';
import { Logger } from './utils/logger';
import { PathUtils } from './utils/pathUtils';
import {
  OTALog,
  ContextCommit,
  SquashResult,
  BranchInfo,
  StatusInfo
} from './models/types';

export class GitContextClient {
  private pythonPath: string;
  private workspaceRoot: string;

  constructor() {
    const config = vscode.workspace.getConfiguration('gitcontext');
    this.pythonPath = config.get<string>('pythonPath', 'python3');

    const root = PathUtils.getWorkspaceRoot();
    if (!root) {
      throw new Error('No workspace folder open');
    }
    this.workspaceRoot = root;
  }

  private async runCommand(args: string[]): Promise<string> {
    const cmd = `${this.pythonPath} -m gitcontext.cli ${args.join(' ')}`;
    Logger.debug(`Running: ${cmd}`);

    try {
      const result = await exec(cmd, { cwd: this.workspaceRoot });
      Logger.debug(`Command output: ${result.stdout}`);
      return result.stdout;
    } catch (error: any) {
      Logger.error(`Command failed: ${cmd}`, error);
      throw new Error(`GitContext command failed: ${error.stderr || error.message}`);
    }
  }

  async init(): Promise<void> {
    await this.runCommand(['init']);
  }

  async createBranch(name: string, fromBranch?: string): Promise<void> {
    const args = ['branch', name];
    if (fromBranch) {
      args.push('--from', fromBranch);
    }
    await this.runCommand(args);
  }

  async checkout(branch: string): Promise<void> {
    await this.runCommand(['checkout', branch]);
  }

  async commit(message: string, otaFile?: string, decisions?: string[]): Promise<string> {
    const args = ['commit', `"${message}"`];
    if (otaFile) {
      args.push('--ota-file', otaFile);
    }
    if (decisions && decisions.length > 0) {
      args.push('--decisions', decisions.join(','));
    }

    const output = await this.runCommand(args);
    // Extract commit ID from output (format: "✅ Commit abc123: message")
    const match = output.match(/Commit ([a-f0-9]+):/);
    return match ? match[1] : 'unknown';
  }

  async merge(branch: string, squash: boolean = true): Promise<SquashResult> {
    const args = ['merge', branch];
    if (!squash) {
      args.push('--no-squash');
    }

    const output = await this.runCommand(args);

    // Try to parse squash result from output
    // In real implementation, we'd save result to file and read it
    // For now, return a basic result
    return {
      decisions: [],
      rejectedAlternatives: [],
      keyInsights: [],
      architectureSummary: 'Merge completed',
      otaCount: 0,
      originalCommits: 0,
      branchName: branch,
      mergedAt: new Date().toISOString()
    };
  }

  async log(branch?: string, limit: number = 10): Promise<ContextCommit[]> {
    const args = ['log'];
    if (branch) {
      args.push('--branch', branch);
    }
    args.push('--limit', limit.toString());
    args.push('--format', 'json');

    const output = await this.runCommand(args);

    try {
      // Parse JSON output (we'd need to modify CLI to support JSON output)
      return JSON.parse(output);
    } catch {
      return [];
    }
  }

  async status(): Promise<StatusInfo> {
    const output = await this.runCommand(['status', '--format', 'json']);

    try {
      return JSON.parse(output);
    } catch {
      // Fallback to reading from files directly
      return this.readStatusFromFiles();
    }
  }

  async recordOta(thought: string, action: string, result: string, filesAffected: string[]): Promise<string> {
    const args = [
      'ota',
      '--thought', `"${thought}"`,
      '--action', `"${action}"`,
      '--result', `"${result}"`
    ];

    if (filesAffected.length > 0) {
      args.push('--files', filesAffected.join(','));
    }

    const output = await this.runCommand(args);

    // Extract filename from output
    const match = output.match(/saved to (.*\.json)/);
    return match ? match[1] : '';
  }

  // Direct file reading (fallback if CLI not working)
  private async readStatusFromFiles(): Promise<StatusInfo> {
    const indexPath = PathUtils.getIndexPath();
    if (!indexPath || !await fs.pathExists(indexPath)) {
      throw new Error('GitContext not initialized');
    }

    const yaml = require('js-yaml');
    const index = yaml.load(await fs.readFile(indexPath, 'utf8'));

    const currentBranch = index.current_branch;
    const branchData = index.branches[currentBranch];

    // Get latest commit
    let latestCommit: string | undefined;
    let latestCommitId: string | undefined;

    if (branchData.current_commit) {
      const commitPath = PathUtils.getCommitPath(currentBranch, branchData.current_commit);
      if (commitPath && await fs.pathExists(commitPath)) {
        const commitData = yaml.load(await fs.readFile(commitPath, 'utf8'));
        latestCommit = commitData.message;
        latestCommitId = commitData.id;
      }
    }

    // Check for uncommitted changes (simplified)
    const tempPath = PathUtils.getTempPath();
    let uncommitted = false;
    if (tempPath) {
      const files = await fs.readdir(tempPath);
      uncommitted = files.some(f => f.startsWith('ota_'));
    }

    return {
      currentBranch,
      commits: branchData.commits.length,
      latestCommit,
      latestCommitId: latestCommitId?.substring(0, 8),
      uncommittedChanges: uncommitted,
      allBranches: Object.keys(index.branches)
    };
  }

  async getBranches(): Promise<BranchInfo[]> {
    const indexPath = PathUtils.getIndexPath();
    if (!indexPath || !await fs.pathExists(indexPath)) {
      return [];
    }

    const yaml = require('js-yaml');
    const index = yaml.load(await fs.readFile(indexPath, 'utf8'));

    const currentBranch = index.current_branch;
    const branches: BranchInfo[] = [];

    for (const [name, data] of Object.entries<any>(index.branches)) {
      branches.push({
        name,
        created: data.created,
        lastModified: data.last_modified,
        currentCommit: data.current_commit,
        commits: data.commits || [],
        parent: data.parent,
        isCurrent: name === currentBranch,
        metadata: data.metadata || {}
      });
    }

    return branches;
  }

  async getCommits(branch: string, limit: number = 20): Promise<ContextCommit[]> {
    const branchPath = PathUtils.getBranchPath(branch);
    if (!branchPath) return [];

    const historyPath = path.join(branchPath, 'history');
    if (!await fs.pathExists(historyPath)) return [];

    const commitDirs = await fs.readdir(historyPath);
    const commits: ContextCommit[] = [];

    for (const dir of commitDirs.slice(-limit)) {
      const commitPath = path.join(historyPath, dir, 'commit.json');
      if (await fs.pathExists(commitPath)) {
        const data = await fs.readJson(commitPath);
        commits.push(data);
      }
    }

    // Sort by timestamp descending
    return commits.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  async getOtaLogs(branch: string, limit: number = 50): Promise<OTALog[]> {
    const otaPath = PathUtils.getOtaLogsPath(branch);
    if (!otaPath || !await fs.pathExists(otaPath)) return [];

    const files = await fs.readdir(otaPath);
    const logs: OTALog[] = [];

    for (const file of files.slice(-limit)) {
      if (file.endsWith('.json')) {
        const logPath = path.join(otaPath, file);
        const data = await fs.readJson(logPath);
        logs.push(data);
      }
    }

    // Sort by timestamp descending
    return logs.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  async getCommit(branch: string, commitId: string): Promise<ContextCommit | null> {
    const commitPath = PathUtils.getCommitPath(branch, commitId);
    if (!commitPath || !await fs.pathExists(commitPath)) {
      return null;
    }

    return await fs.readJson(commitPath);
  }

  async deleteBranch(branch: string): Promise<void> {
    await this.runCommand(['branch', '-d', branch]);
  }
}
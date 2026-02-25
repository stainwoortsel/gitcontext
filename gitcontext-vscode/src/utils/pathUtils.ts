import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs-extra';

export class PathUtils {
  static getWorkspaceRoot(): string | undefined {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
      return undefined;
    }
    return workspaceFolders[0].uri.fsPath;
  }

  static getGitContextPath(): string | undefined {
    const root = this.getWorkspaceRoot();
    if (!root) return undefined;

    const gitcontextPath = path.join(root, '.gitcontext');
    return fs.existsSync(gitcontextPath) ? gitcontextPath : undefined;
  }

  static getIndexPath(): string | undefined {
    const gitcontextPath = this.getGitContextPath();
    return gitcontextPath ? path.join(gitcontextPath, 'index.yaml') : undefined;
  }

  static getBranchPath(branch: string): string | undefined {
    const gitcontextPath = this.getGitContextPath();
    if (!gitcontextPath) return undefined;

    if (branch === 'main') {
      return path.join(gitcontextPath, 'contexts', 'main');
    } else {
      return path.join(gitcontextPath, 'contexts', 'branches', branch);
    }
  }

  static getCommitPath(branch: string, commitId: string): string | undefined {
    const branchPath = this.getBranchPath(branch);
    if (!branchPath) return undefined;

    return path.join(branchPath, 'history', `commit_${commitId}`, 'commit.json');
  }

  static getOtaLogsPath(branch: string): string | undefined {
    const branchPath = this.getBranchPath(branch);
    if (!branchPath) return undefined;

    return path.join(branchPath, 'ota-logs');
  }

  static getTempPath(): string | undefined {
    const gitcontextPath = this.getGitContextPath();
    return gitcontextPath ? path.join(gitcontextPath, 'temp') : undefined;
  }

  static getArchivePath(): string | undefined {
    const gitcontextPath = this.getGitContextPath();
    return gitcontextPath ? path.join(gitcontextPath, 'archive') : undefined;
  }

  static async ensureTempDir(): Promise<string | undefined> {
    const tempPath = this.getTempPath();
    if (tempPath) {
      await fs.ensureDir(tempPath);
    }
    return tempPath;
  }
}
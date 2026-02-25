import * as vscode from 'vscode';
import * as path from 'path';
import { GitContextClient } from './gitcontextClient';
import { Logger } from './utils/logger';
import { TreeItemData, BranchInfo, ContextCommit, OTALog } from './models/types';

export class GitContextTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly data: TreeItemData,
    public readonly tooltip?: string,
    public readonly description?: string
  ) {
    super(label, collapsibleState);
    this.tooltip = tooltip || label;
    this.description = description;

    // Set icon based on type
    switch (data.type) {
      case 'branch':
        this.iconPath = new vscode.ThemeIcon('git-branch');
        this.contextValue = data.type;
        break;
      case 'current-branch':
        this.iconPath = new vscode.ThemeIcon('git-branch', new vscode.ThemeColor('gitDecoration.addedResourceForeground'));
        this.contextValue = 'branch';
        break;
      case 'commit':
        this.iconPath = new vscode.ThemeIcon('git-commit');
        this.contextValue = data.type;
        break;
      case 'ota':
        this.iconPath = new vscode.ThemeIcon('comment');
        this.contextValue = data.type;
        break;
      case 'folder':
        this.iconPath = new vscode.ThemeIcon('folder');
        break;
      case 'file':
        this.iconPath = new vscode.ThemeIcon('file');
        break;
    }
  }
}

export class GitContextTreeDataProvider implements vscode.TreeDataProvider<GitContextTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<GitContextTreeItem | undefined | null> =
    new vscode.EventEmitter<GitContextTreeItem | undefined | null>();
  readonly onDidChangeTreeData: vscode.Event<GitContextTreeItem | undefined | null> =
    this._onDidChangeTreeData.event;

  private client: GitContextClient;

  constructor() {
    this.client = new GitContextClient();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(null);
  }

  getTreeItem(element: GitContextTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: GitContextTreeItem): Promise<GitContextTreeItem[]> {
    try {
      if (!element) {
        // Root level - show branches and recent commits
        return await this.getRootItems();
      } else if (element.data.type === 'branch' || element.data.type === 'current-branch') {
        // Branch level - show commits and OTA logs folder
        return await this.getBranchItems(element.data.branch!);
      } else if (element.data.type === 'folder' && element.data.path === 'commits') {
        // Commits folder - show all commits
        return await this.getCommitItems(element.data.branch!);
      } else if (element.data.type === 'folder' && element.data.path === 'ota') {
        // OTA logs folder - show all logs
        return await this.getOtaLogItems(element.data.branch!);
      }
    } catch (error) {
      Logger.error('Error getting tree children', error);
    }

    return [];
  }

  private async getRootItems(): Promise<GitContextTreeItem[]> {
    const items: GitContextTreeItem[] = [];

    try {
      // Get branches
      const branches = await this.client.getBranches();

      // Add branches section
      const branchesItem = new GitContextTreeItem(
        'Branches',
        vscode.TreeItemCollapsibleState.Expanded,
        { type: 'folder', path: 'branches' }
      );
      items.push(branchesItem);

      // Add each branch as child
      for (const branch of branches) {
        const branchItem = new GitContextTreeItem(
          branch.name,
          vscode.TreeItemCollapsibleState.Collapsed,
          {
            type: branch.isCurrent ? 'current-branch' : 'branch',
            branch: branch.name
          },
          `Last modified: ${new Date(branch.lastModified).toLocaleString()}\nCommits: ${branch.commits.length}`,
          branch.isCurrent ? '✓ current' : undefined
        );
        items.push(branchItem);
      }

      // Add recent commits section
      const currentBranch = branches.find(b => b.isCurrent)?.name || 'main';
      const commits = await this.client.getCommits(currentBranch, 5);

      if (commits.length > 0) {
        const commitsItem = new GitContextTreeItem(
          'Recent Commits',
          vscode.TreeItemCollapsibleState.Expanded,
          { type: 'folder', path: 'recent-commits' }
        );
        items.push(commitsItem);

        for (const commit of commits) {
          const commitItem = new GitContextTreeItem(
            commit.message,
            vscode.TreeItemCollapsibleState.None,
            { type: 'commit', branch: currentBranch, commitId: commit.id },
            new Date(commit.timestamp).toLocaleString(),
            commit.id.substring(0, 8)
          );
          items.push(commitItem);
        }
      }

      // Add OTA logs section
      const otaLogs = await this.client.getOtaLogs(currentBranch, 5);
      if (otaLogs.length > 0) {
        const otaItem = new GitContextTreeItem(
          'Recent OTA Logs',
          vscode.TreeItemCollapsibleState.Expanded,
          { type: 'folder', path: 'recent-ota' }
        );
        items.push(otaItem);

        for (const log of otaLogs) {
          const logItem = new GitContextTreeItem(
            log.thought.substring(0, 50) + (log.thought.length > 50 ? '...' : ''),
            vscode.TreeItemCollapsibleState.None,
            { type: 'ota', branch: currentBranch, logId: log.id },
            `${log.action}: ${log.result}`,
            new Date(log.timestamp).toLocaleTimeString()
          );
          items.push(logItem);
        }
      }

    } catch (error) {
      Logger.error('Error getting root items', error);
    }

    return items;
  }

  private async getBranchItems(branch: string): Promise<GitContextTreeItem[]> {
    const items: GitContextTreeItem[] = [];

    // Commits folder
    items.push(new GitContextTreeItem(
      'Commits',
      vscode.TreeItemCollapsibleState.Collapsed,
      { type: 'folder', branch, path: 'commits' },
      'All commits in this branch'
    ));

    // OTA logs folder
    items.push(new GitContextTreeItem(
      'OTA Logs',
      vscode.TreeItemCollapsibleState.Collapsed,
      { type: 'folder', branch, path: 'ota' },
      'All OTA logs in this branch'
    ));

    return items;
  }

  private async getCommitItems(branch: string): Promise<GitContextTreeItem[]> {
    const items: GitContextTreeItem[] = [];
    const commits = await this.client.getCommits(branch);

    for (const commit of commits) {
      items.push(new GitContextTreeItem(
        commit.message,
        vscode.TreeItemCollapsibleState.None,
        { type: 'commit', branch, commitId: commit.id },
        new Date(commit.timestamp).toLocaleString(),
        commit.id.substring(0, 8)
      ));
    }

    return items;
  }

  private async getOtaLogItems(branch: string): Promise<GitContextTreeItem[]> {
    const items: GitContextTreeItem[] = [];
    const logs = await this.client.getOtaLogs(branch);

    for (const log of logs) {
      items.push(new GitContextTreeItem(
        log.thought.substring(0, 60) + (log.thought.length > 60 ? '...' : ''),
        vscode.TreeItemCollapsibleState.None,
        { type: 'ota', branch, logId: log.id },
        `${log.action} → ${log.result}`,
        new Date(log.timestamp).toLocaleString()
      ));
    }

    return items;
  }
}

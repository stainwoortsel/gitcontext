import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

class GitContextProvider implements vscode.TreeDataProvider<ContextItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ContextItem | undefined | null> =
        new vscode.EventEmitter<ContextItem | undefined | null>();
    readonly onDidChangeTreeData: vscode.Event<ContextItem | undefined | null> =
        this._onDidChangeTreeData.event;

    constructor(private workspaceRoot: string) {}

    refresh(): void {
        this._onDidChangeTreeData.fire(null);
    }

    getTreeItem(element: ContextItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ContextItem): Thenable<ContextItem[]> {
        if (!this.workspaceRoot) {
            vscode.window.showInformationMessage('No workspace open');
            // @ts-ignore
            return Promise.resolve([]);
        }

        const contextPath = path.join(this.workspaceRoot, '.gitcontext');
        if (!fs.existsSync(contextPath)) {
            // @ts-ignore
            return Promise.resolve([new ContextItem(
                'Not initialized',
                'Run "GitContext: Init" to start',
                vscode.TreeItemCollapsibleState.None
            )]);
        }

        if (element) {
            // Return commits for a branch
            return this.getCommitsForBranch(element.label as string);
        } else {
            // Return branches
            return this.getBranches();
        }
    }

    private async getBranches(): Promise<ContextItem[]> {
        try {
            const indexPath = path.join(this.workspaceRoot, '.gitcontext', 'index.yaml');
            const yaml = require('js-yaml');
            const index = yaml.load(fs.readFileSync(indexPath, 'utf8'));

            const branches: ContextItem[] = [];
            for (const [name, data] of Object.entries(index.branches)) {
                const branch = new ContextItem(
                    name,
                    `Commits: ${(data as any).commits.length}`,
                    vscode.TreeItemCollapsibleState.Collapsed
                );
                branch.contextValue = name === index.current_branch ? 'current-branch' : 'branch';
                branch.iconPath = new vscode.ThemeIcon(name === index.current_branch ? 'git-branch' : 'git-branch');
                branches.push(branch);
            }
            return branches;
        } catch (err) {
            return [];
        }
    }

    private async getCommitsForBranch(branchName: string): Promise<ContextItem[]> {
        // Load commits from .gitcontext/contexts/branches/{branchName}/history/
        const commitsPath = path.join(this.workspaceRoot, '.gitcontext', 'contexts', 'branches', branchName, 'history');
        if (!fs.existsSync(commitsPath)) {
            return [];
        }

        const commits = fs.readdirSync(commitsPath);
        return commits.map(commitDir => {
            const commitData = JSON.parse(
                fs.readFileSync(path.join(commitsPath, commitDir, 'commit.json'), 'utf8')
            );
            return new ContextItem(
                commitData.message,
                new Date(commitData.timestamp).toLocaleString(),
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'gitcontext.showCommit',
                    title: 'Show Commit',
                    arguments: [branchName, commitDir]
                }
            );
        });
    }
}

class ContextItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        private descriptionText: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);
        this.description = descriptionText;
        this.tooltip = `${this.label} - ${this.descriptionText}`;
    }
}

export function activate(context: vscode.ExtensionContext) {
    const rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!rootPath) { return; }

    const treeDataProvider = new GitContextProvider(rootPath);
    const treeView = vscode.window.createTreeView('gitcontextView', {
        treeDataProvider,
        showCollapseAll: true
    });

    context.subscriptions.push(
        vscode.commands.registerCommand('gitcontext.init', async () => {
            const terminal = vscode.window.createTerminal('GitContext');
            terminal.sendText('git-context init');
            terminal.show();
            treeDataProvider.refresh();
        }),

        vscode.commands.registerCommand('gitcontext.createBranch', async () => {
            const branchName = await vscode.window.showInputBox({ prompt: 'Branch name' });
            if (branchName) {
                const terminal = vscode.window.createTerminal('GitContext');
                terminal.sendText(`git-context branch ${branchName}`);
                terminal.show();
                treeDataProvider.refresh();
            }
        }),

        vscode.commands.registerCommand('gitcontext.commit', async () => {
            const message = await vscode.window.showInputBox({ prompt: 'Commit message' });
            if (message) {
                const terminal = vscode.window.createTerminal('GitContext');
                terminal.sendText(`git-context commit "${message}"`);
                terminal.show();
                treeDataProvider.refresh();
            }
        }),

        vscode.commands.registerCommand('gitcontext.merge', async (branchItem: ContextItem) => {
            const branchName = branchItem.label as string;
            const squash = await vscode.window.showQuickPick(['Squash (summarize)', 'Full merge'], {
                placeHolder: 'Merge type'
            });

            const terminal = vscode.window.createTerminal('GitContext');
            if (squash === 'Squash (summarize)') {
                terminal.sendText(`git-context merge ${branchName}`);
            } else {
                terminal.sendText(`git-context merge ${branchName} --no-squash`);
            }
            terminal.show();
            treeDataProvider.refresh();
        }),

        vscode.commands.registerCommand('gitcontext.showCommit', (branchName: string, commitId: string) => {
            const panel = vscode.window.createWebviewPanel(
                'gitcontext.commit',
                `Commit: ${commitId}`,
                vscode.ViewColumn.One,
                {}
            );

            const commitPath = path.join(rootPath, '.gitcontext', 'contexts', 'branches', branchName, 'history', commitId, 'commit.json');
            const commitData = JSON.parse(fs.readFileSync(commitPath, 'utf8'));

            panel.webview.html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: var(--vscode-font-family); padding: 20px; }
                        .commit { background: var(--vscode-editor-background); padding: 15px; }
                        .message { font-size: 1.2em; font-weight: bold; }
                        .timestamp { color: var(--vscode-descriptionForeground); }
                        .decisions { margin-top: 20px; }
                        .decision { background: var(--vscode-editor-inactiveSelectionBackground); padding: 10px; margin: 5px 0; }
                    </style>
                </head>
                <body>
                    <div class="commit">
                        <div class="message">${commitData.message}</div>
                        <div class="timestamp">${new Date(commitData.timestamp).toLocaleString()}</div>
                        <div class="decisions">
                            <h3>Decisions</h3>
                            ${commitData.decisions.map(d => `<div class="decision">${d}</div>`).join('')}
                        </div>
                    </div>
                </body>
                </html>
            `;
        })
    );

    // Watch for changes in .gitcontext
    const watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(rootPath, '.gitcontext/**/*')
    );
    watcher.onDidChange(() => treeDataProvider.refresh());
    watcher.onDidCreate(() => treeDataProvider.refresh());
    watcher.onDidDelete(() => treeDataProvider.refresh());
}
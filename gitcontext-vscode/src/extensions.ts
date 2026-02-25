import * as vscode from 'vscode';
import { GitContextTreeDataProvider } from './treeDataProvider';
import { GitContextCommands } from './commands';
import { Logger } from './utils/logger';
import { PathUtils } from './utils/pathUtils';

let treeDataProvider: GitContextTreeDataProvider;
let commands: GitContextCommands;

export function activate(context: vscode.ExtensionContext) {
  Logger.initialize(context);
  Logger.info('GitContext extension activating');

  // Initialize providers
  treeDataProvider = new GitContextTreeDataProvider();
  commands = new GitContextCommands(context);

  // Register tree view
  const treeView = vscode.window.createTreeView('gitcontext-contextView', {
    treeDataProvider,
    showCollapseAll: true
  });

  context.subscriptions.push(treeView);

  // Register all commands
  registerCommands(context);

  // Check if GitContext is initialized in workspace
  checkInitialization();

  // Watch for configuration changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(e => {
      if (e.affectsConfiguration('gitcontext')) {
        Logger.info('Configuration changed, refreshing');
        treeDataProvider.refresh();
      }
    })
  );

  // Watch for file changes in .gitcontext
  const watcher = vscode.workspace.createFileSystemWatcher('**/.gitcontext/**/*');
  watcher.onDidChange(() => treeDataProvider.refresh());
  watcher.onDidCreate(() => treeDataProvider.refresh());
  watcher.onDidDelete(() => treeDataProvider.refresh());
  context.subscriptions.push(watcher);

  // Auto-record OTA on save if enabled
  if (vscode.workspace.getConfiguration('gitcontext').get('autoRecordOta')) {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument(async (document) => {
        // Only trigger if file is in workspace and GitContext is initialized
        if (!PathUtils.getGitContextPath()) return;

        const fileName = vscode.workspace.asRelativePath(document.fileName);
        if (!fileName.startsWith('..')) { // File is in workspace
          const answer = await vscode.window.showInformationMessage(
            `File saved: ${fileName}. Record OTA log?`,
            'Yes', 'No', 'Always'
          );

          if (answer === 'Yes' || answer === 'Always') {
            vscode.commands.executeCommand('gitcontext.recordOta');
          }

          if (answer === 'Always') {
            // TODO: Save preference
          }
        }
      })
    );
  }

  Logger.info('GitContext extension activated');
}

function registerCommands(context: vscode.ExtensionContext) {
  const disposables = [
    vscode.commands.registerCommand('gitcontext.init', () => commands.init()),
    vscode.commands.registerCommand('gitcontext.createBranch', () => commands.createBranch()),
    vscode.commands.registerCommand('gitcontext.commit', () => commands.commit()),
    vscode.commands.registerCommand('gitcontext.merge', (item) => commands.merge(item)),
    vscode.commands.registerCommand('gitcontext.switchBranch', (item) => commands.switchBranch(item)),
    vscode.commands.registerCommand('gitcontext.deleteBranch', (item) => commands.deleteBranch(item)),
    vscode.commands.registerCommand('gitcontext.viewCommit', (item) => commands.viewCommit(item)),
    vscode.commands.registerCommand('gitcontext.viewOtaLog', (item) => commands.viewOtaLog(item)),
    vscode.commands.registerCommand('gitcontext.recordOta', () => commands.recordOta()),
    vscode.commands.registerCommand('gitcontext.status', () => commands.showStatus()),
    vscode.commands.registerCommand('gitcontext.log', () => commands.showLog()),
    vscode.commands.registerCommand('gitcontext.refresh', () => treeDataProvider.refresh())
  ];

  disposables.forEach(d => context.subscriptions.push(d));
}

function checkInitialization() {
  const gitcontextPath = PathUtils.getGitContextPath();

  if (!gitcontextPath) {
    // Show welcome view with init button
    vscode.commands.executeCommand('setContext', 'workspaceHasGitcontext', false);
  } else {
    vscode.commands.executeCommand('setContext', 'workspaceHasGitcontext', true);
  }
}

export function deactivate() {
  Logger.info('GitContext extension deactivated');
}
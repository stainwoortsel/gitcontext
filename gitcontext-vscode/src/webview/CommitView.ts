import * as vscode from 'vscode';
import * as path from 'path';
import { GitContextClient } from '../gitcontextClient';
import { Logger } from '../utils/logger';

export class CommitView {
  public static currentPanel: CommitView | undefined;
  private readonly panel: vscode.WebviewPanel;
  private readonly client: GitContextClient;
  private disposables: vscode.Disposable[] = [];

  private constructor(panel: vscode.WebviewPanel, branch: string, commitId: string) {
    this.panel = panel;
    this.client = new GitContextClient();

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    this.panel.webview.html = this.getLoadingHtml();

    this.loadCommit(branch, commitId);
  }

  public static createOrShow(branch: string, commitId: string) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : vscode.ViewColumn.One;

    if (CommitView.currentPanel) {
      CommitView.currentPanel.panel.reveal(column);
    } else {
      const panel = vscode.window.createWebviewPanel(
        'gitcontext.commitView',
        `Commit: ${commitId.substring(0, 8)}`,
        column || vscode.ViewColumn.One,
        {
          enableScripts: true,
          retainContextWhenHidden: true,
          localResourceRoots: [
            vscode.Uri.file(path.join(__dirname, '../../media'))
          ]
        }
      );

      CommitView.currentPanel = new CommitView(panel, branch, commitId);
    }
  }

  private async loadCommit(branch: string, commitId: string) {
    try {
      const commit = await this.client.getCommit(branch, commitId);
      if (commit) {
        this.panel.webview.html = this.getCommitHtml(commit);
      } else {
        this.panel.webview.html = this.getErrorHtml('Commit not found');
      }
    } catch (error) {
      Logger.error('Error loading commit', error);
      this.panel.webview.html = this.getErrorHtml('Failed to load commit');
    }
  }

  private getLoadingHtml(): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
          }
          .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-size: 1.2em;
          }
        </style>
      </head>
      <body>
        <div class="loading">Loading commit...</div>
      </body>
      </html>
    `;
  }

  private getCommitHtml(commit: any): string {
    const decisions = commit.decisions || [];
    const alternatives = commit.alternatives || [];
    const otaLogs = commit.otaLogs || [];

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
          }
          .header {
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 15px;
            margin-bottom: 20px;
          }
          .commit-id {
            font-size: 0.9em;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 5px;
          }
          .message {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
          }
          .timestamp {
            color: var(--vscode-descriptionForeground);
            margin-bottom: 5px;
          }
          .parent {
            color: var(--vscode-descriptionForeground);
            font-family: monospace;
          }
          .section {
            margin: 25px 0;
          }
          .section-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: var(--vscode-editorLineNumber-activeForeground);
          }
          .decision {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 10px;
            margin: 5px 0;
            border-radius: 3px;
          }
          .alternative {
            background: var(--vscode-inputValidation-warningBackground);
            padding: 10px;
            margin: 5px 0;
            border-radius: 3px;
          }
          .alternative-what {
            font-weight: bold;
            color: var(--vscode-editorWarning-foreground);
          }
          .alternative-why {
            margin-top: 5px;
            color: var(--vscode-descriptionForeground);
          }
          .ota-log {
            background: var(--vscode-textBlockQuote-background);
            padding: 10px;
            margin: 10px 0;
            border-left: 3px solid var(--vscode-textLink-foreground);
          }
          .ota-thought {
            font-style: italic;
            margin-bottom: 5px;
          }
          .ota-action {
            font-weight: bold;
            color: var(--vscode-textLink-foreground);
          }
          .ota-result {
            margin-top: 5px;
            color: var(--vscode-descriptionForeground);
          }
          .files {
            font-family: monospace;
            font-size: 0.9em;
            color: var(--vscode-descriptionForeground);
            margin-top: 5px;
          }
          .badge {
            display: inline-block;
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            margin-left: 10px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="commit-id">${commit.id}</div>
          <div class="message">${commit.message}</div>
          <div class="timestamp">${new Date(commit.timestamp).toLocaleString()}</div>
          ${commit.parent ? `<div class="parent">Parent: ${commit.parent}</div>` : ''}
        </div>

        <div class="section">
          <div class="section-title">
            Decisions <span class="badge">${decisions.length}</span>
          </div>
          ${decisions.map((d: string) => `
            <div class="decision">${d}</div>
          `).join('')}
          ${decisions.length === 0 ? '<p>No decisions recorded</p>' : ''}
        </div>

        <div class="section">
          <div class="section-title">
            Alternatives Considered <span class="badge">${alternatives.length}</span>
          </div>
          ${alternatives.map((alt: any) => `
            <div class="alternative">
              <div class="alternative-what">${alt.what}</div>
              <div class="alternative-why">❌ ${alt.whyRejected}</div>
            </div>
          `).join('')}
          ${alternatives.length === 0 ? '<p>No alternatives recorded</p>' : ''}
        </div>

        <div class="section">
          <div class="section-title">
            OTA Logs <span class="badge">${otaLogs.length}</span>
          </div>
          ${otaLogs.map((log: any) => `
            <div class="ota-log">
              <div class="ota-thought">💭 ${log.thought}</div>
              <div class="ota-action">⚡ ${log.action}</div>
              <div class="ota-result">✅ ${log.result}</div>
              ${log.filesAffected && log.filesAffected.length > 0 ? `
                <div class="files">📁 ${log.filesAffected.join(', ')}</div>
              ` : ''}
            </div>
          `).join('')}
          ${otaLogs.length === 0 ? '<p>No OTA logs</p>' : ''}
        </div>

        <div class="section">
          <div class="section-title">Files Snapshot</div>
          <div class="files">
            ${Object.keys(commit.filesSnapshot || {}).length} files changed
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getErrorHtml(message: string): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-errorForeground);
            background: var(--vscode-editor-background);
          }
          .error {
            text-align: center;
            padding: 50px;
          }
        </style>
      </head>
      <body>
        <div class="error">❌ ${message}</div>
      </body>
      </html>
    `;
  }

  public dispose() {
    CommitView.currentPanel = undefined;
    this.panel.dispose();

    while (this.disposables.length) {
      const x = this.disposables.pop();
      if (x) {
        x.dispose();
      }
    }
  }
}

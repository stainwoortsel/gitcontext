import * as vscode from 'vscode';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export class Logger {
  private static outputChannel: vscode.OutputChannel;
  private static level: LogLevel = LogLevel.INFO;

  static initialize(context: vscode.ExtensionContext) {
    this.outputChannel = vscode.window.createOutputChannel('GitContext');
    context.subscriptions.push(this.outputChannel);

    // Load log level from config
    const config = vscode.workspace.getConfiguration('gitcontext');
    const levelStr = config.get<string>('logLevel', 'info');
    this.level = LogLevel[levelStr.toUpperCase() as keyof typeof LogLevel] || LogLevel.INFO;
  }

  static debug(message: string, data?: any) {
    if (this.level <= LogLevel.DEBUG) {
      this.log('DEBUG', message, data);
    }
  }

  static info(message: string, data?: any) {
    if (this.level <= LogLevel.INFO) {
      this.log('INFO', message, data);
    }
  }

  static warn(message: string, data?: any) {
    if (this.level <= LogLevel.WARN) {
      this.log('WARN', message, data);
    }
  }

  static error(message: string, error?: any) {
    if (this.level <= LogLevel.ERROR) {
      this.log('ERROR', message, error);
    }
  }

  private static log(level: string, message: string, data?: any) {
    const timestamp = new Date().toISOString();
    let logMessage = `[${timestamp}] [${level}] ${message}`;

    if (data) {
      if (data instanceof Error) {
        logMessage += `\n${data.stack || data.message}`;
      } else {
        try {
          logMessage += `\n${JSON.stringify(data, null, 2)}`;
        } catch {
          logMessage += `\n${String(data)}`;
        }
      }
    }

    this.outputChannel.appendLine(logMessage);
  }

  static show() {
    this.outputChannel.show();
  }
}
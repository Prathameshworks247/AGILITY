import * as vscode from 'vscode';
import { getWorkspaceFolder, getCurrentBranch, getDiffForFile } from './git';
import type { ExtensionSettings } from './config';
import { ReviewClient, type SnapshotPayload } from './reviewClient';

const TASK_STORAGE_KEY = 'agilityAI.currentTaskId';
const AUTO_TRACK_STORAGE_KEY = 'agilityAI.autoTrackEnabled';

export class ReviewTracker implements vscode.Disposable {
  private readonly context: vscode.ExtensionContext;
  private readonly client: ReviewClient;
  private settings: ExtensionSettings;
  private readonly output: vscode.OutputChannel;
  private readonly statusItem: vscode.StatusBarItem;
  private autoTrack: boolean;

  constructor(
    context: vscode.ExtensionContext,
    settings: ExtensionSettings,
    client: ReviewClient,
    output: vscode.OutputChannel,
  ) {
    this.context = context;
    this.settings = settings;
    this.client = client;
    this.output = output;

    this.autoTrack =
      this.context.workspaceState.get<boolean>(AUTO_TRACK_STORAGE_KEY) ??
      settings.autoTrack;

    this.statusItem = vscode.window.createStatusBarItem(
      'agilityAIStatus',
      vscode.StatusBarAlignment.Left,
      100,
    );
    this.statusItem.command = 'agilityAI.toggleAutoTracking';
    this.refreshStatusBar();
    this.statusItem.show();
  }

  public updateSettings(settings: ExtensionSettings) {
    this.settings = settings;
    this.client.updateSettings(settings);
    this.refreshStatusBar();
  }

  public dispose() {
    this.statusItem.dispose();
  }

  public getCurrentTaskId(): string | undefined {
    return (
      this.context.workspaceState.get<string>(TASK_STORAGE_KEY) ||
      this.settings.defaultTaskId ||
      undefined
    );
  }

  public async setCurrentTaskId(taskId: string | undefined) {
    if (taskId) {
      await this.context.workspaceState.update(TASK_STORAGE_KEY, taskId.trim());
      vscode.window.showInformationMessage(
        `Agility AI task set to ${taskId.trim()}`,
      );
      this.output.appendLine(
        `[Agility AI] Active task set to ${taskId.trim()}`,
      );
    } else {
      await this.context.workspaceState.update(TASK_STORAGE_KEY, undefined);
      vscode.window.showInformationMessage('Agility AI task cleared.');
      this.output.appendLine('[Agility AI] Active task cleared');
    }
    this.refreshStatusBar();
  }

  public isAutoTrackingEnabled(): boolean {
    return this.autoTrack;
  }

  public async toggleAutoTracking() {
    this.autoTrack = !this.autoTrack;
    await this.context.workspaceState.update(
      AUTO_TRACK_STORAGE_KEY,
      this.autoTrack,
    );
    this.refreshStatusBar();
    vscode.window.showInformationMessage(
      `Agility AI auto tracking ${this.autoTrack ? 'enabled' : 'disabled'}.`,
    );
  }

  private refreshStatusBar() {
    const task = this.getCurrentTaskId();
    const parts = [
      'Agility AI',
      this.autoTrack ? 'Auto: On' : 'Auto: Off',
      task ? `Task: ${task}` : 'Task: —',
    ];
    this.statusItem.text = parts.join(' • ');
    this.statusItem.tooltip =
      'Toggle auto tracking or set task via command palette (Agility AI).';
  }

  public async handleDocumentSaved(document: vscode.TextDocument) {
    if (!this.autoTrack) {
      return;
    }

    if (!this.settings.languages.includes(document.languageId)) {
      return;
    }

    const taskId = this.getCurrentTaskId();
    if (!taskId) {
      this.output.appendLine(
        `[Agility AI] Skipping snapshot for ${document.fileName} because no task is selected.`,
      );
      return;
    }

    const payload = await this.buildSnapshotPayload(document, taskId);
    if (!payload) {
      return;
    }

    await this.safeSendSnapshot(payload);
  }

  public async sendManualSnapshot(document: vscode.TextDocument) {
    const taskId = this.getCurrentTaskId();
    if (!taskId) {
      throw new Error('No task is selected. Run "Agility AI: Set Active Task" first.');
    }
    const payload = await this.buildSnapshotPayload(document, taskId);
    if (!payload) {
      throw new Error('Unable to generate snapshot payload.');
    }
    await this.safeSendSnapshot(payload);
  }

  private async buildSnapshotPayload(
    document: vscode.TextDocument,
    taskId: string,
  ): Promise<SnapshotPayload | undefined> {
    const workspacePath = await getWorkspaceFolder(document);
    if (!workspacePath) {
      this.output.appendLine(
        `[Agility AI] Skipping ${document.fileName} because it is outside the workspace.`,
      );
      return undefined;
    }

    const branch = await getCurrentBranch(workspacePath);
    const diff = await getDiffForFile(workspacePath, document.fileName);

    const payload: SnapshotPayload = {
      taskId,
      developerId: this.settings.developerId || undefined,
      languageId: document.languageId,
      filePath: document.fileName,
      content: document.getText(),
      diff: diff || undefined,
      branch,
      metadata: {
        workspace: workspacePath,
        timestamp: new Date().toISOString(),
      },
    };

    return payload;
  }

  private async safeSendSnapshot(payload: SnapshotPayload) {
    try {
      await this.client.sendSnapshot(payload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : JSON.stringify(error);
      this.output.appendLine(`[Agility AI] ${message}`);
      vscode.window.showErrorMessage(
        `Agility AI snapshot failed: ${message}`,
        'Open Logs',
      ).then((selection) => {
        if (selection === 'Open Logs') {
          this.output.show(true);
        }
      });
    }
  }
}


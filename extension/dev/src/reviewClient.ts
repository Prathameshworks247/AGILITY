import * as vscode from 'vscode';
import type { ExtensionSettings } from './config';

export interface SnapshotPayload {
  taskId: string;
  developerId?: string;
  languageId: string;
  filePath: string;
  content: string;
  diff?: string;
  branch?: string;
  metadata?: Record<string, unknown>;
}

export interface SnapshotResponse {
  acknowledgementId?: string;
  receivedAt?: string;
  message?: string;
}

export class ReviewClient {
  private settings: ExtensionSettings;
  private readonly output: vscode.OutputChannel;

  constructor(settings: ExtensionSettings, output: vscode.OutputChannel) {
    this.settings = settings;
    this.output = output;
  }

  public updateSettings(settings: ExtensionSettings) {
    this.settings = settings;
  }

  public async sendSnapshot(payload: SnapshotPayload): Promise<SnapshotResponse> {
    const baseUrl = this.settings.apiBaseUrl;
    if (!baseUrl) {
      throw new Error('Agility AI API base URL is not configured.');
    }

    const url = `${baseUrl}/v1/snapshots`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'User-Agent': 'agility-ai-vscode-extension',
    };

    if (this.settings.apiToken) {
      headers.Authorization = `Bearer ${this.settings.apiToken}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        ...payload,
        source: 'vscode-extension',
        sentAt: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `Failed to send snapshot: ${response.status} ${response.statusText} - ${text}`,
      );
    }

    const result = (await response.json().catch(() => ({}))) as SnapshotResponse;
    this.output.appendLine(
      `[Agility AI] Snapshot accepted for task ${payload.taskId} (${payload.filePath})`,
    );
    return result;
  }
}


import * as vscode from 'vscode';

export interface ExtensionSettings {
  apiBaseUrl: string;
  apiToken: string;
  defaultTaskId: string;
  developerId: string;
  autoTrack: boolean;
  languages: string[];
}

const SECTION = 'agilityAI';

export function getExtensionSettings(): ExtensionSettings {
  const config = vscode.workspace.getConfiguration(SECTION);
  return {
    apiBaseUrl: config.get<string>('apiBaseUrl', 'http://localhost:8002').replace(/\/+$/, ''),
    apiToken: config.get<string>('apiToken', ''),
    defaultTaskId: config.get<string>('defaultTaskId', ''),
    developerId: config.get<string>('developerId', ''),
    autoTrack: config.get<boolean>('autoTrack', true),
    languages: config.get<string[]>('languages', []),
  };
}

export function observeSettings(
  callback: (settings: ExtensionSettings) => void,
): vscode.Disposable {
  return vscode.workspace.onDidChangeConfiguration((event) => {
    if (event.affectsConfiguration(SECTION)) {
      callback(getExtensionSettings());
    }
  });
}


import { exec } from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';

function runGitCommand(
  workspacePath: string,
  args: string[],
): Promise<string | undefined> {
  return new Promise((resolve) => {
    const command = `git ${args.join(' ')}`;
    exec(
      command,
      { cwd: workspacePath, timeout: 5_000 },
      (error, stdout) => {
        if (error) {
          resolve(undefined);
          return;
        }
        resolve(stdout.trim());
      },
    );
  });
}

export async function getWorkspaceFolder(document: vscode.TextDocument): Promise<string | undefined> {
  const folder = vscode.workspace.getWorkspaceFolder(document.uri);
  return folder?.uri.fsPath;
}

export async function getCurrentBranch(workspacePath: string): Promise<string | undefined> {
  return runGitCommand(workspacePath, ['rev-parse', '--abbrev-ref', 'HEAD']);
}

export async function getDiffForFile(
  workspacePath: string,
  filePath: string,
): Promise<string | undefined> {
  const relativePath = path.relative(workspacePath, filePath);
  const output = await runGitCommand(workspacePath, [
    'diff',
    '--unified=3',
    '--',
    relativePath,
  ]);
  return output;
}


// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { getExtensionSettings, observeSettings } from './config';
import { ReviewClient } from './reviewClient';
import { ReviewTracker } from './reviewTracker';

let tracker: ReviewTracker | undefined;

export async function activate(context: vscode.ExtensionContext) {
	const outputChannel = vscode.window.createOutputChannel('Agility AI');
	context.subscriptions.push(outputChannel);

	const settings = getExtensionSettings();
	const client = new ReviewClient(settings, outputChannel);
	tracker = new ReviewTracker(context, settings, client, outputChannel);
	context.subscriptions.push(tracker);

	const settingsSubscription = observeSettings((updatedSettings) => {
		tracker?.updateSettings(updatedSettings);
	});
	context.subscriptions.push(settingsSubscription);

	const saveListener = vscode.workspace.onDidSaveTextDocument(async (document) => {
		await tracker?.handleDocumentSaved(document);
	});
	context.subscriptions.push(saveListener);

	const setTaskCommand = vscode.commands.registerCommand('agilityAI.setActiveTask', async () => {
		const currentTask = tracker?.getCurrentTaskId();
		const value = await vscode.window.showInputBox({
			title: 'Agility AI: Active Task',
			value: currentTask,
			placeHolder: 'Enter the task ID the current work belongs to',
			prompt: 'Provide the Agility task ID (leave blank to clear).',
		});
		if (value === undefined) {
			return;
		}
		await tracker?.setCurrentTaskId(value.length > 0 ? value : undefined);
	});
	context.subscriptions.push(setTaskCommand);

	const sendSnapshotCommand = vscode.commands.registerCommand('agilityAI.sendSnapshot', async () => {
		const editor = vscode.window.activeTextEditor;
		if (!editor) {
			vscode.window.showWarningMessage('Open a file in the editor before sending a snapshot.');
			return;
		}
		try {
			await tracker?.sendManualSnapshot(editor.document);
			vscode.window.showInformationMessage('Agility AI snapshot sent successfully.');
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error);
			vscode.window.showErrorMessage(`Agility AI snapshot failed: ${message}`);
		}
	});
	context.subscriptions.push(sendSnapshotCommand);

	const toggleAutoTrackingCommand = vscode.commands.registerCommand('agilityAI.toggleAutoTracking', async () => {
		await tracker?.toggleAutoTracking();
	});
	context.subscriptions.push(toggleAutoTrackingCommand);

	outputChannel.appendLine('[Agility AI] Extension activated.');
}

export function deactivate() {
	tracker?.dispose();
	tracker = undefined;
}

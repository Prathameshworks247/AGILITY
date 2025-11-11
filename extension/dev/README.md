# Agility AI Companion

The Agility AI Companion keeps your Scrum Master up to date by streaming code snapshots from VS Code to the Agility AI review service. Each snapshot is analysed by the microservice and surfaced on the Scrum dashboard as an AI review.

## Features

- Auto-tracks saves for selected languages and forwards code snapshots.
- Command palette action to set or clear the active Agility task.
- Toggle auto-tracking directly from the status bar.
- Manually push the current editor buffer for review on demand.
- Output channel logging for transparency and debugging.

## Getting Started

1. Install dependencies and compile once:
   ```bash
   npm install
   npm run compile
   ```
2. Open this folder in VS Code and press `F5` to launch an Extension Development Host.
3. Configure the connection under **Settings → Agility AI Companion**.
4. Run **Agility AI: Set Active Task** to choose the task you’re working on.

## Extension Settings

The extension contributes the following settings:

- `agilityAI.apiBaseUrl` – Base URL for the AI review microservice (default `http://localhost:8002`).
- `agilityAI.apiToken` – Optional bearer token for authenticating requests.
- `agilityAI.defaultTaskId` – Fallback task ID used when no active task is set.
- `agilityAI.developerId` – Agility developer identifier included with snapshots.
- `agilityAI.autoTrack` – Enable automatic snapshot uploads on save.
- `agilityAI.languages` – Language identifiers that should trigger automatic snapshots.

## Commands

- `Agility AI: Set Active Task` (`agilityAI.setActiveTask`)
- `Agility AI: Send Snapshot` (`agilityAI.sendSnapshot`)
- `Agility AI: Toggle Auto Tracking` (`agilityAI.toggleAutoTracking`)

## Status Bar

The left status bar item displays tracking mode and active task. Click it to toggle auto tracking.

## Known Limitations

- Requires a Git workspace to include diffs; otherwise only the full file content is sent.
- The AI review microservice endpoint (`/v1/snapshots`) must be implemented separately.
- Frequent saves may generate high snapshot volume—disable auto tracking if necessary.

## Release Notes

### 0.0.1

Initial scaffold featuring auto tracking, manual snapshots, task selection, and configurable endpoints.


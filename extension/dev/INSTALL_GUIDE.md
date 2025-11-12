# VS Code Extension Installation Guide

## Method 1: Install via VS Code UI (Recommended)

1. **Open VS Code**

2. **Go to Extensions view**:
   - Click the Extensions icon in the sidebar (or press `Cmd+Shift+X` / `Ctrl+Shift+X`)

3. **Install from VSIX**:
   - Click the `...` menu at the top of the Extensions panel
   - Select "Install from VSIX..."
   - Navigate to: `/Users/prathameshpatil/AGILITY/extension/dev/dev-0.0.1.vsix`
   - Click "Install"

4. **Reload VS Code** when prompted

5. **Verify Installation**:
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type "Agility AI"
   - You should see:
     - `Agility AI: Set Active Task`
     - `Agility AI: Send Snapshot`
     - `Agility AI: Toggle Auto Tracking`

## Method 2: Debug Mode (F5)

If Method 1 doesn't work, try debugging:

1. **Open the extension folder in VS Code**:
   ```bash
   cd /Users/prathameshpatil/AGILITY/extension/dev
   code .
   ```

2. **Rebuild the extension**:
   - Open Terminal in VS Code (`Ctrl+``)
   - Run: `node esbuild.js`
   - Wait for "build finished"

3. **Press F5** (or go to Run → Start Debugging)

4. **In the new Extension Development Host window**:
   - Open your project folder
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type "Agility AI" to see commands

5. **Check for errors**:
   - In Extension Development Host: `View` → `Output`
   - Select "Extension Host" from dropdown
   - Look for any error messages

## Method 3: Command Line Installation

1. **Add VS Code to PATH** (if not already):
   - Open VS Code
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type "Shell Command: Install 'code' command in PATH"
   - Click it

2. **Install the extension**:
   ```bash
   code --install-extension /Users/prathameshpatil/AGILITY/extension/dev/dev-0.0.1.vsix
   ```

3. **Restart VS Code**

## Troubleshooting

### Extension doesn't appear in list

**Check if it's installed**:
1. Open Extensions view (`Cmd+Shift+X` / `Ctrl+Shift+X`)
2. Type "Agility AI" in the search box
3. Look for "Agility AI Companion"

**If not found, check the extension host logs**:
1. `View` → `Output`
2. Select "Extension Host" from dropdown
3. Look for errors mentioning "Agility AI" or "agilityAI"

### Commands don't appear

**Reload the window**:
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type "Developer: Reload Window"
3. Press Enter
4. Try the commands again

### Extension activates but commands fail

**Check the Output panel**:
1. `View` → `Output`
2. Select "Agility AI" from dropdown
3. Look for activation message and any errors

### "No workspace folder" error

The extension needs a folder to be open:
1. `File` → `Open Folder...`
2. Select your project folder
3. Try the commands again

## Configuration

After installation, configure the extension:

1. **Open Settings**: `Cmd+,` / `Ctrl+,`

2. **Search for "Agility AI"**

3. **Set required values**:
   - `Agility AI: Api Base Url`: `http://localhost:8002`
   - `Agility AI: Languages`: Add languages you want to track (default includes TypeScript, JavaScript, Python, etc.)
   - `Agility AI: Auto Track`: Enable to auto-send on save

## Usage

1. **Set Active Task**:
   - `Cmd+Shift+P` / `Ctrl+Shift+P` → "Agility AI: Set Active Task"
   - Enter your task ID from the Next.js app

2. **Check Status Bar**:
   - Bottom of VS Code should show: `Agility AI • Auto: On • Task: [your-task-id]`
   - Click it to toggle auto-tracking

3. **Edit Code**:
   - Open a code file
   - Make changes
   - Save (`Cmd+S` / `Ctrl+S`)
   - Check "Agility AI" output panel for confirmation

4. **Manual Snapshot** (optional):
   - `Cmd+Shift+P` / `Ctrl+Shift+P` → "Agility AI: Send Snapshot"
   - Sends current file immediately

## Verify It's Working

1. **Set a task ID** (from your Next.js app)
2. **Open a TypeScript/JavaScript file**
3. **Make a small change** (add a comment)
4. **Save the file**
5. **Check Output panel**: `View` → `Output` → "Agility AI"
   - Should see: "Snapshot accepted for task..."
6. **Check Next.js sprint board**
   - Task should have a review badge

## Need Help?

If the extension still doesn't work:

1. **Rebuild from source**:
   ```bash
   cd /Users/prathameshpatil/AGILITY/extension/dev
   npm install
   node esbuild.js
   ```

2. **Check the logs** in all output panels:
   - "Agility AI"
   - "Extension Host"
   - "Log (Extension Host)"

3. **Verify FastAPI is running**:
   - Open http://localhost:8002 in browser
   - Should see: `{"ok": true, "service": "AGILITY AI Summarizer & Reviewer"}`

4. **Test the API directly**:
   ```bash
   curl -X POST http://localhost:8002/v1/snapshots \
     -H "Content-Type: application/json" \
     -d '{
       "taskId": "test123",
       "languageId": "typescript",
       "filePath": "test.ts",
       "content": "console.log(\"test\");"
     }'
   ```


# Agility AI - Complete Integration Guide

End-to-end guide for setting up the AI code review system with VS Code extension, FastAPI backend, and Next.js frontend.

## System Architecture

```
┌─────────────────┐
│  VS Code        │
│  Extension      │  Developer writes code
│  (Agility AI)   │  & saves files
└────────┬────────┘
         │ POST /v1/snapshots
         │ (code, diff, taskId)
         ▼
┌─────────────────┐
│  FastAPI        │
│  Microservice   │  AI Code Review
│  (Port 8002)    │  (Gemini)
└────────┬────────┘
         │ POST /api/task-reviews
         │ (status, summary, findings)
         ▼
┌─────────────────┐
│  Next.js        │
│  Backend API    │  Store reviews
│  (Port 3000)    │  in MongoDB
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Next.js        │
│  Frontend       │  Scrum Master
│  Sprint Board   │  views reviews
└─────────────────┘
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.12+
- MongoDB Atlas account (or local MongoDB)
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- VS Code

## Step 1: Setup Next.js Application

### 1.1 Install Dependencies

```bash
cd agility-app
npm install
```

### 1.2 Configure Environment

Create `.env` or `.env.local` file:

```env
# Database
DATABASE_URL="mongodb+srv://username:password@cluster.mongodb.net/agility"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"

# Google OAuth (optional)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

# AI Review Service
REVIEW_SERVICE_TOKEN="super-secret-token"
```

### 1.3 Setup Database

```bash
npx prisma generate
npx prisma db push
```

### 1.4 Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

## Step 2: Setup FastAPI Microservice

### 2.1 Install Dependencies

```bash
cd fast-api-backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Configure Environment

Create `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
NEXTJS_API_URL=http://localhost:3000/api/task-reviews
NEXTJS_SERVICE_TOKEN=super-secret-token  # Must match REVIEW_SERVICE_TOKEN
```

### 2.3 Run Development Server

```bash
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8002
```

The API will be available at http://localhost:8002

Test it: http://localhost:8002/docs (FastAPI auto-generated docs)

## Step 3: Install VS Code Extension

### 3.1 Build Extension

```bash
cd extension/dev
npm install
npm run compile
```

### 3.2 Install in VS Code

1. Press `F5` in VS Code (opens Extension Development Host)
2. Or package and install:
   ```bash
   npm install -g @vscode/vsce
   vsce package
   code --install-extension agility-ai-companion-0.0.1.vsix
   ```
### 3.3 Configure Extension

Open VS Code Settings (Cmd/Ctrl + ,) and search for "Agility AI":

```json
{
  "agilityAI.apiBaseUrl": "http://localhost:8002",
  "agilityAI.apiToken": "",  // Optional: if you add auth
  "agilityAI.developerId": "your-user-id",  // Required so reviews are attributed to you
  "agilityAI.autoTrack": true,
  "agilityAI.languages": [
    "typescript",
    "javascript",
    "python",
    "java",
    "go",
    "rust"
  ]
}
```

## Step 4: Complete Workflow Test

### 4.1 Create Organization & Project

1. Open http://localhost:3000
2. Sign up / Sign in
3. Create an organization
4. Create a project
5. Create a sprint

### 4.2 Create a Task

1. Navigate to the sprint board
2. Click "Create Task"
3. Fill in task details (title, description, assignee)
4. Note the task ID (visible in the task card or URL)

### 4.3 Link Task in VS Code

1. Open your project in VS Code
2. Run command: `Agility AI: Set Active Task`
3. Enter the task ID from step 4.2
4. Status bar should show: `Agility AI • Auto: On • Task: [your-task-id]`

### 4.4 Trigger Code Review

1. Open or create a code file (TypeScript, Python, etc.)
2. Make some changes
3. Save the file (Cmd/Ctrl + S)
4. Check the Output panel (`Agility AI` channel) for confirmation

### 4.5 View Review on Sprint Board

1. Go back to the Next.js sprint board
2. Refresh the page
3. The task should now show a review badge (PASS/WARN/FAIL)
4. Click "View Review History" to see detailed findings

## Troubleshooting

### Extension Issues

**Problem**: "No task is selected"
- **Solution**: Run `Agility AI: Set Active Task` and enter a valid task ID

**Problem**: "Failed to send snapshot"
- **Solution**: Check that FastAPI is running on port 8002
- Check Output panel for detailed error messages

### FastAPI Issues

**Problem**: "GEMINI_API_KEY is not set"
- **Solution**: Create `.env` file with your Gemini API key

**Problem**: "Failed to forward review to Next.js"
- **Solution**: Ensure Next.js is running on port 3000
- Check NEXTJS_API_URL in FastAPI `.env`

### Next.js Issues

**Problem**: "Task not found"
- **Solution**: Ensure the task exists in the database
- Check that you're using the correct task ID

**Problem**: "Unauthorized"
- **Solution**: Make sure you're logged in
- Ensure you're a member of the organization

## Advanced Configuration

### Production Deployment

#### FastAPI
```bash
uvicorn summary.main:app --host 0.0.0.0 --port 8002 --workers 4
```

#### Next.js
```bash
npm run build
npm start
```

### Adding Authentication to FastAPI

Update `main.py`:

```python
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    # Verify token against your auth system
    return token

@app.post("/v1/snapshots")
async def receive_snapshot(
    payload: SnapshotPayload,
    token: str = Depends(verify_token)
):
    # ... rest of implementation
```

### Custom Review Criteria

Edit `gemini_client.py` to customize the review prompt:

```python
def review_code(self, diff_text: str) -> str:
    prompt = (
        "Perform a code review focusing on:\n"
        "1. Security vulnerabilities\n"
        "2. Performance issues\n"
        "3. Code quality and maintainability\n"
        "4. Best practices for [your framework]\n"
        # ... customize as needed
    )
```

## API Reference

### FastAPI Endpoints

#### POST /v1/snapshots
Receives code snapshots from VS Code extension.

**Request Body:**
```json
{
  "taskId": "task_id_here",
  "developerId": "user_id",
  "languageId": "typescript",
  "filePath": "/path/to/file.ts",
  "content": "file content",
  "diff": "git diff output",
  "branch": "feature/my-feature",
  "metadata": {
    "workspace": "/path/to/workspace",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

**Response:**
```json
{
  "acknowledgementId": "uuid",
  "receivedAt": "2025-01-01T00:00:00Z",
  "message": "Snapshot received and reviewed. Status: PASS"
}
```

### Next.js Endpoints

#### POST /api/task-reviews
Stores code review results.

**Request Body:**
```json
{
  "taskId": "task_id_here",
  "status": "PASS",
  "summary": "Code review summary",
  "findings": [
    {
      "category": "Security",
      "severity": "high",
      "file": "file.ts",
      "message": "Finding description"
    }
  ]
}
```

#### GET /api/task-reviews?taskId=xxx
Retrieves review history for a task.

**Response:**
```json
{
  "reviews": [
    {
      "id": "review_id",
      "taskId": "task_id",
      "status": "PASS",
      "summary": "Review summary",
      "findings": [...],
      "createdAt": "2025-01-01T00:00:00Z",
      "developer": {
        "id": "user_id",
        "name": "Developer Name",
        "email": "dev@example.com"
      }
    }
  ]
}
```

## Support

For issues or questions:
- Check the logs in VS Code Output panel (`Agility AI`)
- Check FastAPI logs in terminal
- Check Next.js logs in terminal
- Review the documentation in each component's README

## License

MIT


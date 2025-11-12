# Agility AI - FastAPI Backend for Code Reviews

AI-powered code review microservice that integrates with the Agility project management system.

## Features

- **Real-time Code Reviews**: Receives code snapshots from VS Code extension
- **AI Analysis**: Uses Google Gemini to analyze code quality, security, and best practices
- **Automatic Integration**: Forwards review results to Next.js frontend for Scrum Masters
- **Git Integration**: Supports commit summaries and PR reviews

## Setup

1. Create and activate a venv (optional):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file (see ENV_EXAMPLE.md):

```bash
GEMINI_API_KEY=your_gemini_api_key_here
NEXTJS_API_URL=http://localhost:3000/api/task-reviews
```

## Run

For development (with auto-reload):
```bash
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8002
```

For production:
```bash
uvicorn summary.main:app --host 0.0.0.0 --port 8002 --workers 4
```

## API Endpoints

### Core Endpoints

- **GET /** → Health check
- **POST /v1/snapshots** → Receive code snapshots from VS Code extension
  - Accepts: SnapshotPayload (taskId, code, diff, metadata)
  - Returns: SnapshotResponse (acknowledgementId, status)
  - Automatically performs AI review and forwards to Next.js

### Legacy Endpoints (Git-based)

- **GET /summary** → Summarize latest commit or a given commit
  - Query: `commit` (optional)
- **GET /code-review** → Review latest commit or PR range
  - Query: `base_ref` (optional), e.g. `origin/main`

## Integration Flow

1. **Developer** saves code in VS Code with Agility AI Companion extension
2. **Extension** sends snapshot to FastAPI `/v1/snapshots`
3. **FastAPI** performs Gemini AI code review
4. **FastAPI** forwards review results to Next.js `/api/task-reviews`
5. **Scrum Master** sees review badges and details on sprint board

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `NEXTJS_API_URL`: Next.js backend URL (default: http://localhost:3000/api/task-reviews)

### VS Code Extension Settings

Point the extension's `agilityAI.apiBaseUrl` to this service:
```json
{
  "agilityAI.apiBaseUrl": "http://localhost:8002"
}
```

## Review Status Codes

- **PASS**: No significant issues found
- **WARN**: Minor issues or suggestions (medium severity)
- **FAIL**: Critical issues or blockers (high severity, security issues)

## Notes

- The service shells out to `git` for legacy endpoints, so run it inside a Git repo
- Diffs are truncated at ~250KB for token safety
- Review results are parsed and categorized (Bugs, Security, Performance, etc.)
- Failed forwards to Next.js are logged but don't fail the snapshot receipt



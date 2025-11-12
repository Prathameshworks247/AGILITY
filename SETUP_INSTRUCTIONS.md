# Quick Setup Instructions

## 1. Install httpx in FastAPI Backend

```bash
cd fast-api-backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install httpx
```

## 2. Configure Environment Variables

### `fast-api-backend/.env`

```env
GEMINI_API_KEY=your_gemini_api_key_here
NEXTJS_API_URL=http://localhost:3000/api/task-reviews
NEXTJS_SERVICE_TOKEN=super-secret-token
```

### `agility-app/.env.local`

```env
REVIEW_SERVICE_TOKEN=super-secret-token
```

## 3. Start All Services

### Terminal 1: Next.js App
```bash
cd agility-app
npm run dev
```

### Terminal 2: FastAPI Microservice
```bash
cd fast-api-backend
source venv/bin/activate
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8002
```

### Terminal 3: VS Code Extension
1. Open `extension/dev` folder in VS Code
2. Press F5 to launch Extension Development Host
3. Or run: `npm run compile && npm run watch`

## 4. Test the Flow

1. **In Next.js** (http://localhost:3000):
   - Create organization → project → sprint → task
   - Note the task ID

2. **In VS Code Extension Host**:
   - Run command: `Agility AI: Set Active Task`
   - Enter the task ID
   - Open a code file and make changes
   - Save the file (Cmd/Ctrl + S)

3. **Check Results**:
   - FastAPI logs should show: "Snapshot accepted for task..."
   - Next.js sprint board should show review badge on the task
   - Click "View Review History" to see AI findings

## Troubleshooting

If the extension can't connect to FastAPI:
- Verify FastAPI is running: http://localhost:8002
- Check extension settings: `agilityAI.apiBaseUrl` = `http://localhost:8002`

If FastAPI can't forward to Next.js:
- Verify Next.js is running: http://localhost:3000
- Check `.env` in fast-api-backend: `NEXTJS_API_URL` and `NEXTJS_SERVICE_TOKEN`
- Ensure `agility-app/.env.local` has matching `REVIEW_SERVICE_TOKEN`
- Make sure you're logged into Next.js app

## Complete Documentation

See `INTEGRATION_GUIDE.md` for full setup and configuration details.


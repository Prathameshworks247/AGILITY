# AI Code Review System

This document describes the new AI code review flow that powers real-time feedback from developers' editors to the Scrum Master dashboard.

## Overview

```
VS Code Extension ──► AI Review Microservice ──► Agility Backend ──► Next.js UI
```

1. **Extension** collects code changes, pairs them with the current task, and sends them to the microservice.
2. **Microservice** invokes the chosen LLM, receives the annotated review, and posts it back to the Agility backend.
3. **Agility Backend** stores each review so the Scrum Master can monitor progress and blockers.
4. **Next.js UI** renders live review status in the sprint board and provides a detailed history modal.

## Database Schema

```prisma
model TaskReview {
  id          String   @id @default(auto()) @map("_id") @db.ObjectId
  taskId      String   @db.ObjectId
  developerId String   @db.ObjectId
  status      String   // PASS, WARN, FAIL
  summary     String
  findings    Json     // Array of AI findings
  createdAt   DateTime @default(now())

  task      Task @relation(fields: [taskId], references: [id], onDelete: Cascade)
  developer User @relation(fields: [developerId], references: [id], onDelete: Cascade)

  @@index([taskId, createdAt])
}
```

`Task` now has a `reviews` relation so we can pull the latest review when listing tasks.

## REST Endpoints

### Create Review

`POST /api/task-reviews`

```json
{
  "taskId": "task-object-id",
  "status": "WARN",
  "summary": "Consider extracting the validation logic into a shared helper.",
  "findings": [
    {
      "message": "Duplicate validation logic in registration form.",
      "severity": "medium",
      "filePath": "src/app/api/auth/register/route.ts",
      "startLine": 45,
      "endLine": 72
    }
  ]
}
```

Requirements:
- Request must be authenticated.
- Caller must belong to the organization that owns the task.

### Fetch Review History

`GET /api/task-reviews?taskId=<id>&limit=10`

Returns an array of recent reviews ordered by `createdAt` descending.

### Task Listing

`GET /api/tasks?sprintId=<id>`

The response now includes a `latestReview` object per task:

```json
{
  "tasks": [
    {
      "id": "task-id",
      "title": "Implement OAuth callback",
      "status": "IN_PROGRESS",
      "latestReview": {
        "id": "review-id",
        "status": "WARN",
        "summary": "Handle provider error cases",
        "findings": [
          { "message": "Missing fallback for revoked tokens.", "severity": "high" }
        ],
        "createdAt": "2025-01-05T13:21:43.814Z",
        "developer": {
          "name": "Alex Chen",
          "email": "alex@example.com"
        }
      }
    }
  ]
}
```

## Frontend Enhancements

### Sprint Board
- Each task shows an **AI Review badge** with status (Pass / Warnings / Requires Attention).
- A summary snippet highlights the latest feedback.
- “View details” opens a modal with the entire review history and each individual finding.

### Review History Modal
- Lists all historical AI reviews for the task.
- Displays author, timestamp, status, summary, and per-finding metadata.

## Extension → Microservice Contract

**Recommended request payload:**
```json
{
  "taskId": "task-object-id",
  "developerId": "user-object-id",
  "codeSnapshot": {
    "filePath": "src/components/Button.tsx",
    "language": "typescriptreact",
    "content": "<full file or diff>",
    "diff": "<optional git-style diff>"
  },
  "metadata": {
    "branch": "feature/auth",
    "commit": "abc123",
    "testsPassed": true,
    "lintWarnings": []
  }
}
```

**Microservice response (to send back to `/api/task-reviews`):**
```json
{
  "taskId": "task-object-id",
  "status": "WARN",
  "summary": "Coverage dropped for login flow. Add missing tests.",
  "findings": [
    {
      "message": "Add tests for invalid credentials handling.",
      "severity": "medium",
      "filePath": "src/lib/auth.ts",
      "startLine": 120
    },
    {
      "message": "Remove unused helper function `sanitizeCredentials`.",
      "severity": "low"
    }
  ]
}
```

The extension should POST the final review payload to `/api/task-reviews`.

## Security & Access Control

- Only authenticated users can submit or read reviews.
- Developers can post reviews for tasks in organizations they are members of.
- Scrum Masters (or any org member) can review history.
- Findings are stored as JSON; avoid including secrets or PII in the payload.

## Next Steps

- Add service token support so the microservice can authenticate without a user session.
- Stream reviews via WebSockets or SSE for instant dashboard updates.
- Track review resolution by linking findings to follow-up commits or comments.
- Support bulk reviews (e.g., per commit) and PR summarization.




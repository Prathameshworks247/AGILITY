# Agility AI - Real-Time AI-Powered Code Review System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114-green.svg)](https://fastapi.tiangolo.com/)

> Transform your development workflow with real-time AI code reviews directly in your IDE. Link code changes to sprint tasks and give Scrum Masters instant visibility into code quality.

### Team 
- Prathamesh Patil (23bds043)
- Shreevats (23bds055)
- Vishavjeet Yadav (23bds069)
- Yashpreet Singh (23bds072)
- Tanmay Gupta (23bds061)

## 🎯 Overview

Agility AI is a comprehensive code review system that integrates seamlessly into your development workflow. It automatically tracks code changes, performs AI-powered analysis, and displays results in real-time on your sprint board.

### Key Features

- ✨ **Real-Time Code Reviews** - AI analyzes code as you write it
- 🔗 **Task Integration** - Automatically links code to sprint tasks
- 📊 **Visual Dashboard** - Beautiful sprint board with review badges
- 🚀 **Zero Friction** - Works directly in VS Code, no context switching
- 🤖 **AI-Powered** - Uses Google Gemini for intelligent code analysis
- 📈 **Progress Tracking** - Monitor code quality trends over time
- 🔐 **Secure** - Enterprise-grade authentication and access control

## 🏗️ Architecture

```
┌─────────────────┐
│   VS Code       │  Developer writes code
│   Extension     │  & saves files
└────────┬────────┘
         │ POST /v1/snapshots
         │ (code, diff, taskId)
         ▼
┌─────────────────┐
│   FastAPI       │  AI Code Review
│   Microservice  │  (Google Gemini)
│   Port 8002     │
└────────┬────────┘
         │ POST /api/task-reviews
         │ (status, summary, findings)
         ▼
┌─────────────────┐
│   Next.js       │  Store reviews
│   Backend API   │  in MongoDB
│   Port 3000     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Next.js       │  Scrum Master
│   Frontend      │  views reviews
│   Sprint Board  │
└─────────────────┘
```

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/agility-ai.git
cd agility-ai
```

### 2. Start All Services

**Terminal 1 - Next.js App:**
```bash
cd agility-app
npm install
npx prisma generate
npx prisma db push
npm run dev
```

**Terminal 2 - FastAPI Microservice:**
```bash
cd fast-api-backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8002
```

**Terminal 3 - Install VS Code Extension:**
```bash
cd extension/dev
npm install
npm run compile
# Then install agility-ai-companion-0.0.2.vsix in VS Code
```

### 3. Configure & Use

1. **Set up environment variables** (see [Configuration](#configuration))
2. **Open Next.js app** at http://localhost:3000
3. **Create organization → project → sprint → task**
4. **Copy task ID** from the sprint board
5. **In VS Code**: Set active task and start coding!

## 📦 Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.12+
- **MongoDB** Atlas account (or local MongoDB)
- **Google Gemini API Key** ([Get one here](https://makersuite.google.com/app/apikey))
- **VS Code** (for the extension)

## 🔧 Installation

### Next.js Application

```bash
cd agility-app
npm install
npx prisma generate
npx prisma db push
```

### FastAPI Microservice

```bash
cd fast-api-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### VS Code Extension

```bash
cd extension/dev
npm install
npm run compile
```

## ⚙️ Configuration

### Next.js App (`.env`)

```env
# Database
DATABASE_URL="mongodb+srv://username:password@cluster.mongodb.net/agility"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"

# Service Token (for FastAPI → Next.js communication)
REVIEW_SERVICE_TOKEN="your-shared-secret-token"

# Google OAuth (optional)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
```

### FastAPI Microservice (`.env`)

```env
# Gemini API
GEMINI_API_KEY="your_gemini_api_key_here"

# Next.js Backend
NEXTJS_API_URL="http://localhost:3000/api/task-reviews"
NEXTJS_SERVICE_TOKEN="your-shared-secret-token"  # Must match Next.js token
```

### VS Code Extension Settings

Open VS Code Settings (`Cmd+,` / `Ctrl+,`) and configure:

```json
{
  "agilityAI.apiBaseUrl": "http://localhost:8002",
  "agilityAI.apiToken": "",  // Optional
  "agilityAI.developerId": "your-user-id",  // Get from Next.js session
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

## 📖 Usage

### For Developers

1. **Set Active Task**
   - Open sprint board in Next.js
   - Copy task ID from task card
   - In VS Code: `Cmd+Shift+P` → "Agility AI: Set Active Task"
   - Paste task ID

2. **Code & Review**
   - Edit files normally
   - Save file (`Cmd+S` / `Ctrl+S`)
   - Check Output panel for confirmation

3. **View Results**
   - Refresh sprint board
   - See review badge on task
   - Click "View Review History" for details

### For Scrum Masters

1. **View Sprint Board**
   - Navigate to project → sprint
   - See review badges on all tasks

2. **Review Details**
   - Click "View Review History" on any task
   - See all AI reviews with findings
   - Track code quality trends

## 📚 API Documentation

### FastAPI Endpoints

#### `POST /v1/snapshots`
Receive code snapshots from VS Code extension.

**Request:**
```json
{
  "taskId": "task-id",
  "developerId": "user-id",
  "languageId": "typescript",
  "filePath": "/path/to/file.ts",
  "content": "file content",
  "diff": "git diff output",
  "branch": "feature/my-feature"
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

#### `GET /docs`
Interactive API documentation (Swagger UI)

### Next.js API Routes

#### `POST /api/task-reviews`
Create a new code review.

**Headers:**
```
Authorization: Bearer <service-token>
```

**Body:**
```json
{
  "taskId": "task-id",
  "status": "PASS",
  "summary": "Review summary",
  "findings": [
    {
      "category": "Security",
      "severity": "high",
      "file": "file.ts",
      "message": "Finding description"
    }
  ],
  "developerId": "user-id"
}
```

#### `GET /api/task-reviews?taskId=xxx&limit=10`
Get review history for a task.

#### `GET /api/tasks?sprintId=xxx`
Get tasks with latest review data.

## 📁 Project Structure

```
agility-ai/
├── agility-app/              # Next.js frontend & backend
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   │   ├── (app)/       # Authenticated routes
│   │   │   └── api/         # API routes
│   │   └── components/      # React components
│   ├── prisma/
│   │   └── schema.prisma    # Database schema
│   └── package.json
│
├── fast-api-backend/         # AI review microservice
│   ├── summary/
│   │   ├── main.py          # FastAPI app
│   │   ├── gemini_client.py # AI integration
│   │   └── git_utils.py    # Git helpers
│   └── requirements.txt
│
├── extension/                # VS Code extension
│   └── dev/
│       ├── src/
│       │   ├── extension.ts # Main extension
│       │   ├── reviewClient.ts
│       │   ├── reviewTracker.ts
│       │   └── config.ts
│       └── package.json
│
└── README.md
```

## 🛠️ Development

### Running in Development Mode

**Next.js:**
```bash
cd agility-app
npm run dev
```

**FastAPI:**
```bash
cd fast-api-backend
source venv/bin/activate
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8002
```

**VS Code Extension:**
```bash
cd extension/dev
npm run watch
# Press F5 in VS Code to launch Extension Development Host
```

### Database Migrations

```bash
cd agility-app
npx prisma migrate dev
# or
npx prisma db push
```

### Building for Production

**Next.js:**
```bash
cd agility-app
npm run build
npm start
```

**FastAPI:**
```bash
cd fast-api-backend
uvicorn summary.main:app --host 0.0.0.0 --port 8002 --workers 4
```

**VS Code Extension:**
```bash
cd extension/dev
npm run package
# Creates .vsix file for distribution
```

## 🐛 Troubleshooting

### Extension Issues

**Problem**: Commands don't appear
- **Solution**: Reload VS Code window (`Cmd+Shift+P` → "Developer: Reload Window")

**Problem**: "fetch failed" error
- **Solution**: Ensure FastAPI is running on port 8002
- Check `agilityAI.apiBaseUrl` in settings

**Problem**: "No task is selected"
- **Solution**: Run "Agility AI: Set Active Task" and enter a valid task ID

### FastAPI Issues

**Problem**: "GEMINI_API_KEY is not set"
- **Solution**: Create `.env` file with your Gemini API key

**Problem**: "Failed to forward review to Next.js"
- **Solution**: 
  - Ensure Next.js is running on port 3000
  - Check `NEXTJS_API_URL` in `.env`
  - Verify `NEXTJS_SERVICE_TOKEN` matches Next.js token

### Next.js Issues

**Problem**: "Unauthorized" when FastAPI posts reviews
- **Solution**: Set `REVIEW_SERVICE_TOKEN` in Next.js `.env` and match it in FastAPI `.env`

**Problem**: Reviews not showing on sprint board
- **Solution**: 
  - Refresh the page
  - Check browser console for errors
  - Verify reviews exist in database (use Prisma Studio)

## 📊 Features in Detail

### AI Code Review Categories

- 🐛 **Bugs**: Logic errors, edge cases, potential runtime issues
- 🔒 **Security**: Vulnerabilities, best practices, security patterns
- ⚡ **Performance**: Optimization opportunities, efficiency improvements
- 🏗️ **Maintainability**: Code structure, readability, complexity
- 🧪 **Testing**: Test coverage, test quality, missing tests
- 🎨 **Style**: Code style, conventions, formatting

### Review Status Levels

- ✅ **PASS**: No significant issues found
- ⚠️ **WARN**: Minor issues or suggestions (medium severity)
- ❌ **FAIL**: Critical issues or blockers (high severity, security)

### Sprint Board Features

- **Review Badges**: Color-coded status indicators on each task
- **Summary Display**: First 500 characters of review summary
- **Findings Count**: Number of AI findings per review
- **Review History**: Complete modal with all reviews and details
- **Developer Attribution**: See who submitted each review
- **Timeline**: When reviews were created

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript/JavaScript best practices
- Write tests for new features
- Update documentation
- Follow the existing code style
- Add comments for complex logic

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Next.js](https://nextjs.org/) - React framework
- [FastAPI](https://fastapi.tiangolo.com/) - Python web framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI code analysis
- [Prisma](https://www.prisma.io/) - Database ORM
- [VS Code Extension API](https://code.visualstudio.com/api) - Extension platform

## 📞 Support

- 📖 **Documentation**: See `INTEGRATION_GUIDE.md` for detailed setup
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/agility-ai/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/agility-ai/discussions)
- 📧 **Email**: support@agility-ai.com

## 🗺️ Roadmap

- [ ] Real-time updates via WebSocket/SSE
- [ ] Multi-LLM support (OpenAI, Anthropic, etc.)
- [ ] PR integration
- [ ] Analytics dashboard
- [ ] Custom review rules
- [ ] Multi-IDE support (IntelliJ, Vim, etc.)
- [ ] Team metrics and reporting

---

**Made with ❤️ by the Agility AI Team**

For detailed setup instructions, see [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)


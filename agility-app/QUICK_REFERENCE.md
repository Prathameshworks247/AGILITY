# Agility - Quick Reference Guide

## 🚀 Getting Started

### Environment Setup
1. Copy `.env.local` with your MongoDB connection string
2. Run `npm install`
3. Run `npx prisma db push` to sync database
4. Run `npm run dev` to start development server

### First User Setup
1. Navigate to `/sign-up`
2. Create account with email/password
3. Choose your role:
   - **Scrum Master** → Create and manage organizations
   - **Developer** → Join teams and track tasks

## 👥 User Roles

### Scrum Master
- **Purpose**: Manage teams, projects, and sprints
- **Dashboard**: `/dashboard/[orgSlug]`
- **Can**:
  - Create organizations
  - Generate invite codes
  - Create projects and sprints
  - Assign tasks to developers
  - View analytics and reports
  - Manage team members

### Developer
- **Purpose**: View and complete assigned tasks
- **Dashboard**: `/developer-dashboard`
- **Can**:
  - Join organizations (with invite code)
  - View assigned tasks
  - Update task status
  - See personal metrics
  - Comment on tasks

## 🔐 Authentication Flow

```
Sign Up → Create Account
   ↓
Select Role → Scrum Master or Developer
   ↓
Scrum Master:          Developer:
Create Organization → Join with Code
   ↓                      ↓
Get Invite Code → Developer Dashboard
   ↓
Share with Team
   ↓
Organization Dashboard
```

## 📋 Key Pages

| Page | Route | Access | Purpose |
|------|-------|--------|---------|
| Sign In | `/sign-in` | Public | User authentication |
| Sign Up | `/sign-up` | Public | New user registration |
| Role Selection | `/create-org` | Authenticated | Choose role & setup |
| Scrum Dashboard | `/dashboard/[slug]` | Scrum Masters | Manage org/projects |
| Dev Dashboard | `/developer-dashboard` | Developers | View personal tasks |
| Project View | `/project/[slug]` | All | View project details |
| Sprint View | `/sprint/[id]` | All | View sprint details |

## 🔑 Invite Code System

### Format
```
ABC-123-XYZ
```
- 9 alphanumeric characters
- Hyphenated for readability
- Case-insensitive
- Unique per organization

### Usage
1. Scrum Master creates organization → Gets invite code
2. Share code with developers (via email, Slack, etc.)
3. Developer enters code on join page
4. Developer becomes organization member
5. Developer can now be assigned tasks

## 🛠️ API Endpoints

### User APIs
- `POST /api/user/role` - Set user role
- `GET /api/user/profile` - Get user info
- `GET /api/tasks/my-tasks` - Get assigned tasks

### Organization APIs
- `POST /api/organizations` - Create org (returns invite code)
- `POST /api/organizations/join` - Join org with code
- `GET /api/organizations` - List user's orgs

### Task APIs
- `GET /api/tasks/my-tasks` - Get developer's tasks
- (More task APIs to be documented)

## 📊 Database Models

### Core Models
- **User** - Authentication & profile (role: scrumMaster | developer)
- **Organization** - Company/team container (has inviteCode)
- **OrganizationMember** - User-org relationship
- **Project** - Work container
- **Sprint** - Time-boxed iteration
- **Task** - Work items assigned to developers

## 🎨 UI Components

### Role Selection
- Two card options (Scrum Master / Developer)
- Icon-based visual distinction
- Feature list for each role

### Scrum Dashboard
- Organization stats
- Project list
- Sprint timeline
- Team metrics
- Charts (burndown, velocity)

### Developer Dashboard
- Task statistics cards
- Personal task list
- Status indicators
- Priority badges
- Quick filters

## 🔒 Security

### Protected Routes
- All `/dashboard/*` routes require authentication
- `/developer-dashboard` requires authentication
- `/create-org` requires authentication
- Role-based access enforced on dashboard

### Middleware
```typescript
// Protected routes in middleware.ts
- /dashboard/:path*
- /developer-dashboard
- /project/:path*
- /sprint/:path*
- /create-org
```

## 💡 Common Tasks

### As Scrum Master

**Create New Organization**
1. Sign in
2. Go to `/create-org`
3. Select "Scrum Master"
4. Fill in org details
5. Copy invite code from success screen
6. Share with team

**Assign Tasks**
1. Navigate to project
2. Select sprint
3. Create or edit task
4. Assign to developer
5. Set priority and story points

### As Developer

**Join Organization**
1. Sign in
2. Go to `/create-org`
3. Select "Developer"
4. Enter invite code from Scrum Master
5. Access developer dashboard

**View Tasks**
1. Navigate to `/developer-dashboard`
2. See all assigned tasks
3. Filter by status/priority
4. Click "View" to see details
5. Update status as you work

## 🐛 Debugging

### Check User Role
```javascript
// In browser console or API
fetch('/api/user/profile').then(r => r.json()).then(console.log)
```

### Check Organizations
```javascript
fetch('/api/organizations').then(r => r.json()).then(console.log)
```

### Check Tasks (Developer)
```javascript
fetch('/api/tasks/my-tasks').then(r => r.json()).then(console.log)
```

## 📝 Environment Variables

Required in `.env.local`:
```env
DATABASE_URL="mongodb+srv://..."
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key"
NEXT_PUBLIC_OAUTH_ENABLED="false"
NODE_ENV="development"
```

## 🔄 Typical Workflow

### Sprint Planning (Scrum Master)
1. Create project
2. Create sprint with dates
3. Create tasks for sprint
4. Assign tasks to developers
5. Set story points

### Development (Developer)
1. Check developer dashboard
2. View assigned tasks
3. Update status: TODO → IN_PROGRESS → DONE
4. View task details and requirements
5. Collaborate via comments

### Monitoring (Scrum Master)
1. View sprint progress
2. Check burndown chart
3. Review team velocity
4. Identify blockers
5. Adjust sprint as needed

## 🆘 Support

### Common Issues

**Can't see tasks**
- Verify you're in an organization
- Check with Scrum Master for task assignments
- Ensure you're in the correct sprint

**Wrong dashboard**
- Sign out and sign back in
- Check your role via `/api/user/profile`
- Contact admin if role is incorrect

**Invalid invite code**
- Verify code with Scrum Master
- Check for typos (code is case-insensitive)
- Ensure code hasn't been regenerated

## 📚 Further Reading

- `ROLE_BASED_SYSTEM.md` - Detailed role system documentation
- `prisma/README.md` - Database schema documentation
- `prisma/CHART_DATA_GUIDE.md` - Chart implementation guide
- `AUTH_SETUP.md` - Authentication configuration (if exists)


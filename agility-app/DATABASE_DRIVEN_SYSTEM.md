# Database-Driven System Documentation

## Overview

The Agility platform is now fully database-driven with no dummy/mock data. All data is fetched from MongoDB via Prisma and displayed dynamically.

## ✅ Completed Features

### 1. **Organization Dashboard** (`/dashboard/[orgId]`)

**Features:**
- Real-time organization data display
- Team members list with roles (Scrum Master / Developer)
- Invite code display with copy functionality
- Project creation form
- Projects list with real counts (sprints, tasks, members)

**API Endpoints Used:**
- `GET /api/organizations` - Get user's organizations
- `GET /api/organizations/[orgId]/members` - Get team members
- `POST /api/projects` - Create new project
- `GET /api/projects?organizationId=[id]` - Get projects for organization

### 2. **Project Dashboard** (`/project/[projectId]`)

**Features:**
- Project details with organization breadcrumb
- Sprint creation form
- Sprints list with real data
- Sprint progress indicators
- Days remaining calculator for active sprints

**API Endpoints Used:**
- `GET /api/projects?organizationId=[id]` - Get project by slug
- `GET /api/sprints?projectId=[id]` - Get sprints for project
- `POST /api/sprints` - Create new sprint

### 3. **Sprint Dashboard** (`/project/[projectId]/sprint/[sprintId]`)

**Features:**
- Kanban board with 4 columns (To Do, In Progress, In Review, Done)
- Task creation form
- Task editing form
- Drag-free status updates via dropdown
- Real-time task counts and story points
- Developer assignment dropdown
- Priority badges and status badges

**API Endpoints Used:**
- `GET /api/tasks?sprintId=[id]` - Get tasks for sprint
- `POST /api/tasks` - Create new task
- `PATCH /api/tasks` - Update task
- `GET /api/organizations/[orgId]/members` - Get team members for assignment

### 4. **Developer Dashboard** (`/developer-dashboard`)

**Features:**
- Personal task list across all projects
- Task statistics (Total, To Do, In Progress, Done)
- Task details with project and sprint info
- Status and priority indicators
- Quick navigation to task details

**API Endpoints Used:**
- `GET /api/tasks/my-tasks` - Get all tasks assigned to current user

## 🗄️ Database Models Used

### Organization
```prisma
model Organization {
  id          String   @id @default(auto()) @map("_id") @db.ObjectId
  name        String
  slug        String   @unique
  description String?
  inviteCode  String   @unique
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  members     OrganizationMember[]
  projects    Project[]
}
```

### Project
```prisma
model Project {
  id             String   @id @default(auto()) @map("_id") @db.ObjectId
  name           String
  slug           String   @unique
  description    String?
  organizationId String   @db.ObjectId
  startDate      DateTime?
  endDate        DateTime?
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt
  
  organization   Organization @relation(fields: [organizationId], references: [id], onDelete: Cascade)
  sprints        Sprint[]
  tasks          Task[]
  members        ProjectMember[]
}
```

### Sprint
```prisma
model Sprint {
  id              String   @id @default(auto()) @map("_id") @db.ObjectId
  name            String
  goal            String?
  projectId       String   @db.ObjectId
  startDate       DateTime
  endDate         DateTime
  status          String   @default("PLANNING") // PLANNING, ACTIVE, COMPLETED
  plannedPoints   Int      @default(0)
  completedPoints Int      @default(0)
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  project         Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  tasks           Task[]
}
```

### Task
```prisma
model Task {
  id          String   @id @default(auto()) @map("_id") @db.ObjectId
  title       String
  description String?
  projectId   String   @db.ObjectId
  sprintId    String?  @db.ObjectId
  assigneeId  String?  @db.ObjectId
  createdById String   @db.ObjectId
  status      String   @default("TODO") // TODO, IN_PROGRESS, IN_REVIEW, DONE
  priority    String   @default("MEDIUM") // LOW, MEDIUM, HIGH
  storyPoints Int?
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  project     Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  sprint      Sprint? @relation(fields: [sprintId], references: [id], onDelete: SetNull)
  assignee    User?   @relation("AssignedTasks", fields: [assigneeId], references: [id])
  createdBy   User    @relation("CreatedTasks", fields: [createdById], references: [id])
  comments    Comment[]
  activities  Activity[]
}
```

## 📡 API Routes Reference

### Projects API (`/api/projects`)

**POST - Create Project**
```typescript
Body: {
  name: string;
  description?: string;
  organizationId: string;
  startDate?: string;
  endDate?: string;
}
Response: { project: Project }
```

**GET - List Projects**
```typescript
Query: { organizationId: string }
Response: { projects: Project[] }
```

### Sprints API (`/api/sprints`)

**POST - Create Sprint**
```typescript
Body: {
  name: string;
  goal?: string;
  projectId: string;
  startDate: string;
  endDate: string;
  plannedPoints?: number;
}
Response: { sprint: Sprint }
```

**GET - List Sprints**
```typescript
Query: { projectId: string }
Response: { sprints: Sprint[] }
```

### Tasks API (`/api/tasks`)

**POST - Create Task**
```typescript
Body: {
  title: string;
  description?: string;
  projectId: string;
  sprintId?: string;
  assigneeId?: string;
  status?: string;
  priority?: string;
  storyPoints?: number;
}
Response: { task: Task }
```

**GET - List Tasks**
```typescript
Query: { 
  projectId?: string;
  sprintId?: string;
}
Response: { tasks: Task[] }
```

**PATCH - Update Task**
```typescript
Body: {
  taskId: string;
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  storyPoints?: number;
  assigneeId?: string;
  sprintId?: string;
}
Response: { task: Task }
```

### Organization Members API (`/api/organizations/[orgId]/members`)

**GET - List Members**
```typescript
Response: { 
  members: {
    id: string;
    role: string;
    user: {
      id: string;
      name: string;
      email: string;
      role: string;
    };
  }[]
}
```

### My Tasks API (`/api/tasks/my-tasks`)

**GET - Get User's Tasks**
```typescript
Response: { 
  tasks: Task[]
}
```

## 🎯 User Workflows

### Scrum Master Workflow

1. **Sign In** → Redirected to organization dashboard
2. **View Team** → See all developers and scrum masters
3. **Copy Invite Code** → Share with developers
4. **Create Project** → Click "Create New Project" card
5. **Create Sprint** → Navigate to project, click "Create Sprint"
6. **Create Tasks** → Navigate to sprint, click "Create Task"
7. **Assign Tasks** → Select developer from dropdown
8. **Track Progress** → View task status on kanban board

### Developer Workflow

1. **Sign In** → Redirected to developer dashboard
2. **View Tasks** → See all assigned tasks across projects
3. **Navigate to Sprint** → Click on task to view in sprint
4. **Update Status** → Change task status via dropdown
5. **View Details** → See task priority, story points, sprint info

## 🔒 Security & Access Control

All API routes verify:
1. User is authenticated (via NextAuth session)
2. User has access to the organization/project/sprint
3. User role is appropriate for the action

**Scrum Masters Can:**
- Create projects
- Create sprints
- Create tasks
- Edit tasks
- Assign tasks to developers
- View all organization data

**Developers Can:**
- View assigned tasks
- Update task status
- View project and sprint details
- Comment on tasks

## 🚀 Getting Started

### For Scrum Masters

1. Sign up and select "Scrum Master" role
2. Create an organization
3. Copy the invite code
4. Share invite code with your team
5. Create a project
6. Create sprints for the project
7. Add tasks to sprints
8. Assign tasks to developers

### For Developers

1. Sign up and select "Developer" role
2. Enter invite code from your Scrum Master
3. View your developer dashboard
4. Check assigned tasks
5. Update task status as you work

## 📊 Data Flow

### Creating a Project
```
User clicks "Create Project" 
  → Opens dialog form
  → Fills in name, description
  → Submits form
  → POST /api/projects
  → Prisma creates project in MongoDB
  → Returns project data
  → Dashboard refreshes
  → New project appears in list
```

### Creating a Task
```
User clicks "Create Task" in sprint
  → Opens dialog form
  → Fills in title, description, priority, assignee, story points
  → Submits form
  → POST /api/tasks
  → Prisma creates task in MongoDB
  → Links to project and sprint
  → Links to assignee (developer)
  → Returns task data
  → Sprint board refreshes
  → New task appears in "To Do" column
```

### Updating Task Status
```
Developer changes status dropdown
  → onChange event triggers
  → PATCH /api/tasks with new status
  → Prisma updates task in MongoDB
  → Returns updated task
  → Sprint board refreshes
  → Task moves to new column
```

## 🎨 UI Components

### Dialogs
- **Create Project Dialog** - Form for project creation
- **Create Sprint Dialog** - Form for sprint creation with date pickers
- **Create Task Dialog** - Comprehensive task form with assignment
- **Edit Task Dialog** - Update task details

### Cards
- **Project Card** - Shows project stats (sprints, tasks, members)
- **Sprint Card** - Shows sprint timeline, status, progress
- **Task Card** - Shows task details with inline status update

### Lists
- **Team Members List** - Displays all organization members with roles
- **Kanban Board** - 4-column layout for task status

## 🔄 Real-Time Updates

The system uses optimistic UI updates:
1. Action is triggered (e.g., create task)
2. API call is made
3. On success, data is refetched
4. UI updates with new data

For better UX, consider implementing:
- WebSocket connections for real-time updates
- Optimistic UI updates (update UI before API response)
- Loading states for all actions

## 📝 Notes

- All dates are stored as ISO strings in MongoDB
- Slug generation is automatic for projects (lowercase, hyphenated)
- Sprint status is auto-calculated based on dates
- Task status changes trigger completion point updates (future feature)
- Organization invite codes are unique and generated automatically

## 🐛 Troubleshooting

### "Project not found"
- Ensure project slug in URL matches database
- Check user has access to organization

### "Failed to load data"
- Check API route logs in terminal
- Verify Prisma Client is up to date
- Ensure MongoDB connection is active

### "Cannot assign task"
- Verify user is a member of the organization
- Check user role is "developer" or "scrumMaster"
- Ensure user ID exists in database

### Empty dashboards
- Create data using the UI forms
- Verify API routes are returning data
- Check browser console for errors

## 🎓 Best Practices

1. **Always validate input** - Both client and server side
2. **Handle errors gracefully** - Show user-friendly messages
3. **Provide loading states** - Show spinners during data fetches
4. **Refetch after mutations** - Keep UI in sync with database
5. **Use TypeScript** - Catch type errors early
6. **Test API routes** - Use tools like Postman or Thunder Client
7. **Monitor performance** - Watch for slow queries
8. **Optimize queries** - Use Prisma's include/select wisely

## 🔮 Future Enhancements

- [ ] Real-time updates via WebSockets
- [ ] Task comments and activity feed
- [ ] File attachments on tasks
- [ ] Sprint retrospectives
- [ ] Burndown charts with real data
- [ ] Velocity tracking
- [ ] Time tracking
- [ ] Custom fields for tasks
- [ ] Task dependencies
- [ ] Bulk task operations
- [ ] Export to CSV/PDF
- [ ] Mobile app
- [ ] Notifications system
- [ ] Search and filters
- [ ] Dark mode persistence


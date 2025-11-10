# Database Schema Documentation

## Overview

This database schema is designed for an **Agile Project Management** platform with developer productivity tracking, burnout prevention, and real-time collaboration features.

## Database Models

### 🔐 Authentication Models (NextAuth.js Compatible)

#### **User**
Core user model with authentication support.
- Supports both **OAuth** (Google, GitHub) and **credential-based** authentication
- Tracks user roles: `user`, `admin`, `scrumMaster`
- Relations: accounts, sessions, organization/project memberships, tasks, activities, metrics

#### **Account**
OAuth provider accounts linked to users (NextAuth.js standard).

#### **Session**
Active user sessions (NextAuth.js standard).

#### **VerificationToken**
Email verification tokens for passwordless authentication.

---

### 🏢 Organizational Hierarchy

#### **Organization**
Top-level entity representing a company or team.
- **Fields**: name, slug (unique URL identifier), description, image
- **Contains**: Multiple projects and organization members

#### **OrganizationMember**
Junction table for user membership in organizations.
- **Roles**: `owner`, `admin`, `member`
- Links users to organizations with specific permissions

#### **Project**
Projects within an organization (e.g., "Mobile App", "Website Redesign").
- **Fields**: name, slug, description, status, date range
- **Status values**: `active`, `archived`, `completed`
- **Contains**: Sprints, team members, activities

#### **ProjectMember**
Junction table for user membership in projects.
- **Roles**: `scrumMaster`, `productOwner`, `developer`
- Tracks when users join projects

---

### 🏃 Agile/Scrum Models

#### **Sprint**
Time-boxed iteration for work completion (typically 1-4 weeks).
- **Fields**: name, number, goal, status, start/end dates
- **Status values**: `planned`, `active`, `completed`, `cancelled`
- **Contains**: Tasks/stories
- Unique per project by sprint number

#### **Task**
Work items (user stories, bugs, tasks, epics).
- **Types**: `story`, `bug`, `task`, `epic`
- **Status**: `todo`, `inProgress`, `inReview`, `done`
- **Priority**: `low`, `medium`, `high`, `critical`
- **Fields**: title, description, storyPoints, tags
- Can be assigned to a user and linked to a sprint
- Supports comments

#### **Comment**
Comments on tasks for collaboration.
- Links to task and user (author)

---

### 📊 Productivity & Analytics Models

#### **Activity**
Real-time activity feed for projects.
- **Types**: `commit`, `pr`, `flow`, `taskUpdate`, `statusChange`
- Tracks developer actions with metadata (PR numbers, commit hashes, etc.)
- Indexed by project and creation date for fast queries

#### **DeveloperMetric**
Daily developer productivity metrics.
- **Daily Metrics**:
  - Commits count
  - Pull requests count
  - Hours worked
  - Tasks completed
- **Flow State**: Minutes spent in deep focus
- **Burnout Prevention**:
  - Weekly hours tracking
  - Burnout risk level (`low`, `medium`, `high`)
- Unique per user per day for accurate tracking

---

## Key Relationships

```
Organization
  └── Projects (1:N)
       └── Sprints (1:N)
            └── Tasks (1:N)
                 └── Comments (1:N)

User
  ├── OrganizationMember (N:M)
  ├── ProjectMember (N:M)
  ├── Tasks (Assigned) (1:N)
  ├── Activities (1:N)
  └── DeveloperMetrics (1:N)
```

## Usage Examples

### Creating a New Project

```typescript
const project = await prisma.project.create({
  data: {
    name: "Project Agility",
    slug: "project-agility",
    organizationId: "org-id",
    status: "active",
    members: {
      create: [
        { userId: "user-id", role: "scrumMaster" }
      ]
    }
  }
});
```

### Creating a Sprint with Tasks

```typescript
const sprint = await prisma.sprint.create({
  data: {
    name: "Sprint 3",
    number: 3,
    projectId: "project-id",
    status: "active",
    startDate: new Date(),
    endDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 2 weeks
    tasks: {
      create: [
        {
          title: "Implement user authentication",
          type: "story",
          priority: "high",
          storyPoints: 5,
          creatorId: "user-id",
          status: "todo"
        }
      ]
    }
  }
});
```

### Tracking Developer Metrics

```typescript
const metric = await prisma.developerMetric.upsert({
  where: {
    userId_date: {
      userId: "user-id",
      date: new Date()
    }
  },
  update: {
    commits: { increment: 1 },
    hoursWorked: { increment: 2 }
  },
  create: {
    userId: "user-id",
    date: new Date(),
    commits: 1,
    hoursWorked: 2
  }
});
```

### Fetching Project with All Data

```typescript
const project = await prisma.project.findUnique({
  where: { id: "project-id" },
  include: {
    organization: true,
    members: {
      include: { user: true }
    },
    sprints: {
      include: {
        tasks: {
          include: {
            assignee: true,
            comments: true
          }
        }
      }
    },
    activities: {
      include: { user: true },
      orderBy: { createdAt: 'desc' },
      take: 20
    }
  }
});
```

## Next Steps

1. **Set up MongoDB connection**:
   ```bash
   # Add to .env file
   DATABASE_URL="mongodb+srv://username:password@cluster.mongodb.net/database"
   ```

2. **Push schema to database**:
   ```bash
   npx prisma db push
   ```

3. **Generate Prisma Client** (already done):
   ```bash
   npx prisma generate
   ```

4. **Open Prisma Studio** (GUI for database):
   ```bash
   npx prisma studio
   ```

## Features Enabled by This Schema

✅ Multi-tenant organizations with projects  
✅ Agile/Scrum sprint management  
✅ Task tracking with status, priority, and assignments  
✅ Real-time activity feeds  
✅ Developer productivity metrics  
✅ Burnout risk tracking  
✅ Flow state monitoring  
✅ Team collaboration with comments  
✅ NextAuth.js authentication integration  
✅ Flexible role-based access control

## Notes

- Uses **MongoDB** with ObjectId primary keys
- All timestamps are UTC
- Cascade deletes ensure data integrity
- Unique constraints prevent duplicate memberships
- Indexed fields for optimized queries


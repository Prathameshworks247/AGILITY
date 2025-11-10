# Prisma Quick Start Guide

## ✅ What's Been Set Up

1. **Complete Database Schema** - 12 models covering:
   - Authentication (User, Account, Session)
   - Organizations & Projects
   - Sprints & Tasks
   - Activities & Metrics

2. **Prisma Client Generated** - Ready to use in your app

3. **Database Connection** - Configured in `src/lib/db.ts`

---

## 🚀 Getting Started

### 1. Set Up MongoDB Database

Create a `.env` file in the project root:

```bash
DATABASE_URL="mongodb+srv://username:password@cluster.mongodb.net/agility?retryWrites=true&w=majority"
NEXTAUTH_SECRET="generate-with: openssl rand -base64 32"
NEXTAUTH_URL="http://localhost:3000"
```

### 2. Push Schema to Database

```bash
cd agility-app
npx prisma db push
```

This creates all collections in MongoDB.

### 3. Open Prisma Studio (Database GUI)

```bash
npx prisma studio
```

Opens at `http://localhost:5555` - view/edit data visually.

---

## 📝 Common Usage Patterns

### Import Prisma Client

```typescript
import { db } from '@/lib/db';
```

### Create Organization & Project

```typescript
// Create organization
const org = await db.organization.create({
  data: {
    name: "Acme Inc",
    slug: "acme-inc",
    members: {
      create: {
        userId: userId,
        role: "owner"
      }
    }
  }
});

// Create project in organization
const project = await db.project.create({
  data: {
    name: "Project Agility",
    slug: "project-agility",
    organizationId: org.id,
    status: "active"
  }
});
```

### Create Sprint & Tasks

```typescript
const sprint = await db.sprint.create({
  data: {
    name: "Sprint 1",
    number: 1,
    projectId: project.id,
    status: "active",
    startDate: new Date(),
    endDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
    tasks: {
      create: [
        {
          title: "Setup authentication",
          type: "story",
          status: "todo",
          priority: "high",
          storyPoints: 5,
          creatorId: userId
        }
      ]
    }
  }
});
```

### Update Task Status

```typescript
await db.task.update({
  where: { id: taskId },
  data: {
    status: "inProgress",
    assigneeId: userId
  }
});
```

### Track Developer Activity

```typescript
// Log activity
await db.activity.create({
  data: {
    type: "commit",
    message: "Fixed authentication bug",
    projectId: projectId,
    userId: userId,
    metadata: {
      commitHash: "abc123",
      filesChanged: 3
    }
  }
});

// Update daily metrics
await db.developerMetric.upsert({
  where: {
    userId_date: {
      userId: userId,
      date: new Date()
    }
  },
  update: {
    commits: { increment: 1 },
    hoursWorked: { increment: 2 }
  },
  create: {
    userId: userId,
    date: new Date(),
    commits: 1,
    hoursWorked: 2,
    pullRequests: 0,
    tasksCompleted: 0
  }
});
```

### Fetch Dashboard Data

```typescript
// Get project with all nested data
const projectData = await db.project.findUnique({
  where: { id: projectId },
  include: {
    organization: true,
    members: {
      include: {
        user: {
          select: {
            id: true,
            name: true,
            email: true,
            image: true
          }
        }
      }
    },
    sprints: {
      where: { status: "active" },
      include: {
        tasks: {
          include: {
            assignee: true
          }
        }
      }
    },
    activities: {
      take: 20,
      orderBy: { createdAt: 'desc' },
      include: {
        user: true
      }
    }
  }
});
```

### Get Team Metrics

```typescript
const teamMetrics = await db.developerMetric.findMany({
  where: {
    userId: { in: teamMemberIds },
    date: {
      gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) // Last 7 days
    }
  },
  include: {
    user: true
  },
  orderBy: {
    date: 'desc'
  }
});
```

---

## 🔥 Next.js API Route Examples

### `/api/projects/[id]/route.ts`

```typescript
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const project = await db.project.findUnique({
      where: { id: params.id },
      include: {
        sprints: true,
        members: {
          include: { user: true }
        }
      }
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(project);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch project' },
      { status: 500 }
    );
  }
}
```

### `/api/sprints/[id]/tasks/route.ts`

```typescript
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    const task = await db.task.create({
      data: {
        title: body.title,
        description: body.description,
        type: body.type,
        priority: body.priority,
        storyPoints: body.storyPoints,
        sprintId: body.sprintId,
        creatorId: body.userId,
        status: 'todo'
      }
    });

    return NextResponse.json(task);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create task' },
      { status: 500 }
    );
  }
}
```

---

## 📊 Key Models Reference

| Model | Purpose | Key Fields |
|-------|---------|-----------|
| `User` | Authentication & user data | email, name, role |
| `Organization` | Top-level tenant | name, slug |
| `Project` | Work projects | name, status, organizationId |
| `Sprint` | Time-boxed iterations | name, number, startDate, endDate |
| `Task` | Work items | title, status, priority, storyPoints |
| `Activity` | Real-time feed | type, message, metadata |
| `DeveloperMetric` | Daily productivity | commits, hoursWorked, burnoutRisk |

---

## 🛠️ Useful Commands

```bash
# Generate Prisma Client (after schema changes)
npx prisma generate

# Push schema changes to database
npx prisma db push

# Open Prisma Studio GUI
npx prisma studio

# Format schema file
npx prisma format

# View database schema
npx prisma db pull

# Reset database (⚠️ deletes all data)
npx prisma db push --force-reset
```

---

## 🔐 NextAuth Integration

Your schema is **NextAuth.js compatible**. Configure in `pages/api/auth/[...nextauth].ts`:

```typescript
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import { db } from "@/lib/db";
import NextAuth from "next-auth";

export default NextAuth({
  adapter: PrismaAdapter(db),
  // ... your auth config
});
```

---

## 📚 Resources

- [Prisma Docs](https://www.prisma.io/docs)
- [NextAuth.js](https://next-auth.js.org/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

**Ready to build! 🚀**


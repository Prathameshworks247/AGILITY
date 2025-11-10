# Chart Data Guide

## ✅ All Chart Data is Now Included!

Your schema now supports **all chart types** shown in your UI.

---

## 📊 Chart Data Models

### 1. **Developer Activity Chart** (7 Days)
**Model:** `DeveloperMetric`

Shows commits, PRs, and hours worked per day.

```typescript
// Fetch last 7 days of metrics for a team
const metrics = await db.developerMetric.findMany({
  where: {
    userId: { in: teamMemberIds },
    date: {
      gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    }
  },
  include: {
    user: {
      select: { name: true, email: true }
    }
  },
  orderBy: { date: 'asc' }
});

// Transform for chart
const chartData = metrics.reduce((acc, metric) => {
  const day = metric.date.toLocaleDateString('en', { weekday: 'short' });
  const existing = acc.find(d => d.day === day);
  
  if (existing) {
    existing.commits += metric.commits;
    existing.prs += metric.pullRequests;
    existing.hours += metric.hoursWorked;
  } else {
    acc.push({
      day,
      commits: metric.commits,
      prs: metric.pullRequests,
      hours: metric.hoursWorked
    });
  }
  
  return acc;
}, []);
```

---

### 2. **Team Burnout Risk Chart**
**Model:** `DeveloperMetric`

Shows weekly hours and burnout risk per developer.

```typescript
// Get latest weekly metrics for team
const developers = await db.user.findMany({
  where: {
    projectMemberships: {
      some: { projectId: projectId }
    }
  },
  include: {
    metrics: {
      where: {
        date: {
          gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        }
      }
    }
  }
});

// Calculate weekly totals and burnout risk
const burnoutData = developers.map(dev => {
  const weeklyHours = dev.metrics.reduce((sum, m) => sum + m.hoursWorked, 0);
  
  return {
    name: dev.name,
    hours: weeklyHours,
    risk: weeklyHours > 50 ? 'high' : weeklyHours > 40 ? 'medium' : 'low'
  };
});
```

---

### 3. **Sprint Burndown Chart** ⭐ NEW
**Model:** `SprintBurndown`

Shows ideal vs actual remaining work throughout the sprint.

#### Creating Daily Burndown Data

```typescript
// Called daily (can be a cron job or background task)
async function updateSprintBurndown(sprintId: string) {
  const sprint = await db.sprint.findUnique({
    where: { id: sprintId },
    include: {
      tasks: {
        where: { status: { not: 'done' } }
      }
    }
  });

  if (!sprint) return;

  const totalPoints = sprint.plannedPoints || 0;
  const remainingPoints = sprint.tasks.reduce(
    (sum, task) => sum + (task.storyPoints || 0), 
    0
  );
  const completedPoints = totalPoints - remainingPoints;
  
  // Calculate ideal remaining (linear burndown)
  const sprintDays = Math.ceil(
    (sprint.endDate.getTime() - sprint.startDate.getTime()) / (1000 * 60 * 60 * 24)
  );
  const daysPassed = Math.ceil(
    (Date.now() - sprint.startDate.getTime()) / (1000 * 60 * 60 * 24)
  );
  const idealRemaining = Math.max(
    0, 
    totalPoints - (totalPoints / sprintDays) * daysPassed
  );

  // Store burndown data point
  await db.sprintBurndown.upsert({
    where: {
      sprintId_date: {
        sprintId,
        date: new Date()
      }
    },
    update: {
      actualRemaining: remainingPoints,
      idealRemaining: Math.round(idealRemaining),
      completed: completedPoints
    },
    create: {
      sprintId,
      date: new Date(),
      actualRemaining: remainingPoints,
      idealRemaining: Math.round(idealRemaining),
      completed: completedPoints
    }
  });
}
```

#### Fetching Burndown Chart Data

```typescript
const burndownData = await db.sprintBurndown.findMany({
  where: { sprintId },
  orderBy: { date: 'asc' }
});

// Transform for chart
const chartData = burndownData.map((point, index) => ({
  day: `Day ${index + 1}`,
  ideal: point.idealRemaining,
  actual: point.actualRemaining
}));
```

---

### 4. **Velocity Chart** ⭐ NEW
**Model:** `Sprint` (plannedPoints, completedPoints)

Shows planned vs completed story points across sprints.

#### Updating Sprint Points

```typescript
// When sprint starts, calculate planned points
const plannedPoints = await db.task.aggregate({
  where: { 
    sprintId,
    storyPoints: { not: null }
  },
  _sum: { storyPoints: true }
});

await db.sprint.update({
  where: { id: sprintId },
  data: { 
    plannedPoints: plannedPoints._sum.storyPoints || 0 
  }
});

// When sprint completes, calculate completed points
const completedPoints = await db.task.aggregate({
  where: { 
    sprintId,
    status: 'done',
    storyPoints: { not: null }
  },
  _sum: { storyPoints: true }
});

await db.sprint.update({
  where: { id: sprintId },
  data: { 
    completedPoints: completedPoints._sum.storyPoints || 0,
    status: 'completed'
  }
});
```

#### Fetching Velocity Chart Data

```typescript
const sprints = await db.sprint.findMany({
  where: { 
    projectId,
    status: { in: ['completed', 'active'] }
  },
  orderBy: { number: 'asc' },
  take: 10 // Last 10 sprints
});

// Transform for chart
const velocityData = sprints.map(sprint => ({
  sprint: sprint.name,
  planned: sprint.plannedPoints || 0,
  completed: sprint.completedPoints || 0
}));
```

---

## 🔄 Real-Time Updates

### Track Task Status Changes

```typescript
// When task status changes
await db.task.update({
  where: { id: taskId },
  data: { status: 'done', completedAt: new Date() }
});

// Log activity
await db.activity.create({
  data: {
    type: 'statusChange',
    message: `Task completed: ${task.title}`,
    projectId: task.sprint.projectId,
    userId: userId,
    metadata: {
      taskId: task.id,
      oldStatus: 'inProgress',
      newStatus: 'done'
    }
  }
});

// Update burndown (if in active sprint)
if (task.sprint.status === 'active') {
  await updateSprintBurndown(task.sprintId);
}

// Update developer metrics
await db.developerMetric.upsert({
  where: {
    userId_date: {
      userId,
      date: new Date()
    }
  },
  update: {
    tasksCompleted: { increment: 1 }
  },
  create: {
    userId,
    date: new Date(),
    tasksCompleted: 1
  }
});
```

---

## 📈 Summary: All Charts Covered

| Chart | Model | Fields | Status |
|-------|-------|--------|--------|
| **Developer Activity** | `DeveloperMetric` | commits, pullRequests, hoursWorked | ✅ Ready |
| **Burnout Risk** | `DeveloperMetric` | weeklyHours, burnoutRisk | ✅ Ready |
| **Sprint Burndown** | `SprintBurndown` | idealRemaining, actualRemaining | ✅ Ready |
| **Velocity** | `Sprint` | plannedPoints, completedPoints | ✅ Ready |
| **Real-Time Activity** | `Activity` | type, message, metadata | ✅ Ready |

---

## 🚀 API Route Example

### `/api/charts/sprint-burndown/[sprintId]/route.ts`

```typescript
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { sprintId: string } }
) {
  try {
    const burndownData = await db.sprintBurndown.findMany({
      where: { sprintId: params.sprintId },
      orderBy: { date: 'asc' }
    });

    const chartData = burndownData.map((point, index) => ({
      day: `Day ${index + 1}`,
      ideal: point.idealRemaining,
      actual: point.actualRemaining
    }));

    return NextResponse.json(chartData);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch burndown data' },
      { status: 500 }
    );
  }
}
```

### `/api/charts/velocity/[projectId]/route.ts`

```typescript
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { projectId: string } }
) {
  try {
    const sprints = await db.sprint.findMany({
      where: { 
        projectId: params.projectId,
        status: { in: ['completed', 'active'] }
      },
      orderBy: { number: 'desc' },
      take: 10
    });

    const velocityData = sprints.reverse().map(sprint => ({
      sprint: sprint.name,
      planned: sprint.plannedPoints || 0,
      completed: sprint.completedPoints || 0
    }));

    return NextResponse.json(velocityData);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch velocity data' },
      { status: 500 }
    );
  }
}
```

---

## ⚡ Background Jobs (Optional)

For production, consider setting up cron jobs to update metrics:

```typescript
// pages/api/cron/update-burndown.ts
import { db } from '@/lib/db';

export default async function handler(req, res) {
  // Verify cron secret
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Update all active sprints
  const activeSprints = await db.sprint.findMany({
    where: { status: 'active' }
  });

  for (const sprint of activeSprints) {
    await updateSprintBurndown(sprint.id);
  }

  res.json({ updated: activeSprints.length });
}
```

**All chart data is now fully supported!** 📊✨


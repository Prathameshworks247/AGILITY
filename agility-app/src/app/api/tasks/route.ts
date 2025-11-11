import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { Prisma } from '@prisma/client';
import { db } from '@/lib/db';

// Create a new task
export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { 
      title, 
      description, 
      projectId, 
      sprintId, 
      assigneeId, 
      status, 
      priority, 
      storyPoints 
    } = await req.json();

    if (!title || !projectId) {
      return NextResponse.json(
        { error: 'Title and project are required' },
        { status: 400 }
      );
    }

    // Get user who is creating the task
    const creator = await db.user.findUnique({
      where: { email: session.user.email },
    });

    if (!creator) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Verify user has access to the project
    const project = await db.project.findUnique({
      where: { id: projectId },
      include: {
        organization: {
          include: {
            members: {
              where: {
                user: {
                  email: session.user.email,
                },
              },
            },
          },
        },
      },
    });

    if (!project || project.organization.members.length === 0) {
      return NextResponse.json(
        { error: 'You do not have access to this project' },
        { status: 403 }
      );
    }

    // Create task
    const taskData = {
      title,
      description: description ?? null,
      projectId,
      sprintId: sprintId || null,
      assigneeId: assigneeId || null,
      creatorId: creator.id,
      status: (status || 'TODO').toUpperCase(),
      priority: (priority || 'MEDIUM').toUpperCase(),
      storyPoints:
        typeof storyPoints === 'number'
          ? storyPoints
          : storyPoints
          ? Number(storyPoints)
          : null,
    } as Prisma.TaskUncheckedCreateInput;

    const task = await db.task.create({
      data: taskData,
      include: {
        assignee: {
          select: {
            id: true,
            name: true,
            email: true,
            image: true,
          },
        },
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        sprint: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    });

    return NextResponse.json({ task }, { status: 201 });
  } catch (error) {
    console.error('[CREATE_TASK_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to create task' },
      { status: 500 }
    );
  }
}

// Get tasks for a project or sprint
export async function GET(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(req.url);
    const projectId = searchParams.get('projectId');
    const sprintId = searchParams.get('sprintId');

    if (!projectId && !sprintId) {
      return NextResponse.json(
        { error: 'Project ID or Sprint ID is required' },
        { status: 400 }
      );
    }

    // Build where clause
    const where: any = {};
    if (sprintId) {
      where.sprintId = sprintId;
    } else if (projectId) {
    where.projectId = projectId;
    }

    const taskQuery: Prisma.TaskFindManyArgs = {
      where,
      include: {
        assignee: {
          select: {
            id: true,
            name: true,
            email: true,
            image: true,
          },
        },
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        sprint: {
          select: {
            id: true,
            name: true,
          },
        },
      },
      orderBy: [
        { status: 'asc' },
        { priority: 'desc' },
        { createdAt: 'desc' },
      ],
    };

    const tasks = await db.task.findMany(taskQuery);

    const taskIds = tasks.map((task) => task.id);
    const reviewMap = new Map<
      string,
      {
        id: string;
        status: string;
        summary: string;
        findings: unknown[];
        createdAt: Date;
        developer:
          | {
              id: string;
              name: string | null;
              email: string;
            }
          | null;
      }
    >();

    if (taskIds.length > 0) {
      const reviews = await (db as any).taskReview.findMany({
        where: { taskId: { in: taskIds } },
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          taskId: true,
          status: true,
          summary: true,
          findings: true,
          createdAt: true,
          developer: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
        },
      });

      for (const review of reviews) {
        if (!reviewMap.has(review.taskId)) {
          reviewMap.set(review.taskId, {
            id: review.id,
            status: review.status,
            summary: review.summary,
            findings: review.findings ?? [],
            createdAt: review.createdAt,
            developer: review.developer,
          });
        }
      }
    }

    const formatted = tasks.map((task) => {
      const latestReview = reviewMap.get(task.id);
      return {
        ...task,
        latestReview: latestReview
          ? {
              id: latestReview.id,
              status: latestReview.status,
              summary: latestReview.summary,
              findings: latestReview.findings ?? [],
              createdAt: latestReview.createdAt,
              developer: latestReview.developer,
            }
          : null,
      };
    });

    return NextResponse.json({ tasks: formatted });
  } catch (error) {
    console.error('[GET_TASKS_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to fetch tasks' },
      { status: 500 }
    );
  }
}

// Update a task
export async function PATCH(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { 
      taskId, 
      title, 
      description, 
      status, 
      priority, 
      storyPoints, 
      assigneeId,
      sprintId,
    } = await req.json();

    if (!taskId) {
      return NextResponse.json(
        { error: 'Task ID is required' },
        { status: 400 }
      );
    }

    // Verify task exists and user has access
    const existingTask = await db.task.findUnique({
      where: { id: taskId },
      include: {
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
    });


    // Build update data
    const updateData: any = {};
    if (title !== undefined) updateData.title = title;
    if (description !== undefined) updateData.description = description ?? null;
    if (typeof status === 'string') updateData.status = status.toUpperCase();
    if (typeof priority === 'string') updateData.priority = priority.toUpperCase();
    if (storyPoints !== undefined) {
      updateData.storyPoints = storyPoints === null ? null : Number(storyPoints);
    }
    if (assigneeId !== undefined) {
      updateData.assigneeId = assigneeId === '' ? null : assigneeId;
    }
    if (sprintId !== undefined) {
      updateData.sprintId = sprintId === '' ? null : sprintId;
    }

    // Update task
    const task = await db.task.update({
      where: { id: taskId },
      data: updateData,
      include: {
        assignee: {
          select: {
            id: true,
            name: true,
            email: true,
            image: true,
          },
        },
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        sprint: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    });

    return NextResponse.json({ task });
  } catch (error) {
    console.error('[UPDATE_TASK_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to update task' },
      { status: 500 }
    );
  }
}


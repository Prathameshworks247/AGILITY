import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/db';

// Create a new sprint
export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { name, goal, projectId, startDate, endDate, plannedPoints } = await req.json();

    if (!name || !projectId || !startDate || !endDate) {
      return NextResponse.json(
        { error: 'Sprint name, project, start date, and end date are required' },
        { status: 400 }
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

    // Determine sprint status based on dates
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    let status = 'PLANNING';
    if (now >= start && now <= end) {
      status = 'ACTIVE';
    } else if (now > end) {
      status = 'COMPLETED';
    }

    // Create sprint
    const sprint = await db.sprint.create({
      data: {
        name,
        number: 1,
        goal,
        projectId,
        startDate: start,
        endDate: end,
        status,
      },
      include: {
        project: {
          select: {
            name: true,
            slug: true,
          },
        },
      },
    });

    return NextResponse.json({ sprint }, { status: 201 });
  } catch (error) {
    console.error('[CREATE_SPRINT_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to create sprint' },
      { status: 500 }
    );
  }
}

// Get sprints for a project
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

    if (!projectId) {
      return NextResponse.json(
        { error: 'Project ID is required' },
        { status: 400 }
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

    const sprints = await db.sprint.findMany({
      where: {
        projectId,
      },
      include: {
        _count: {
          select: {
            tasks: true,
          },
        },
      },
      orderBy: {
        startDate: 'desc',
      },
    });

    return NextResponse.json({ sprints });
  } catch (error) {
    console.error('[GET_SPRINTS_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to fetch sprints' },
      { status: 500 }
    );
  }
}


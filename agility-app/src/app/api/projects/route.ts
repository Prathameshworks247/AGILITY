import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/db';

// Create a new project
export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { name, description, organizationId, startDate, endDate } = await req.json();

    if (!name || !organizationId) {
      return NextResponse.json(
        { error: 'Project name and organization are required' },
        { status: 400 }
      );
    }

    // Verify user is a member of the organization
    const membership = await db.organizationMember.findFirst({
      where: {
        organizationId,
        user: {
          email: session.user.email,
        },
      },
    });

    if (!membership) {
      return NextResponse.json(
        { error: 'You are not a member of this organization' },
        { status: 403 }
      );
    }

    // Create slug from name
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');

    // Create project
    const project = await db.project.create({
      data: {
        name,
        slug,
        description,
        organizationId,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null,
      },
      include: {
        organization: {
          select: {
            name: true,
            slug: true,
          },
        },
      },
    });

    return NextResponse.json({ project }, { status: 201 });
  } catch (error) {
    console.error('[CREATE_PROJECT_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to create project' },
      { status: 500 }
    );
  }
}

// Get projects for an organization
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
    const organizationId = searchParams.get('organizationId');

    if (!organizationId) {
      return NextResponse.json(
        { error: 'Organization ID is required' },
        { status: 400 }
      );
    }

    // Verify user is a member of the organization
    const membership = await db.organizationMember.findFirst({
      where: {
        organizationId,
        user: {
          email: session.user.email,
        },
      },
    });

    if (!membership) {
      return NextResponse.json(
        { error: 'You are not a member of this organization' },
        { status: 403 }
      );
    }

    const projects = await db.project.findMany({
      where: {
        organizationId,
      },
      include: {
        _count: {
          select: {
            sprints: true,
            members: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    return NextResponse.json({ projects });
  } catch (error) {
    console.error('[GET_PROJECTS_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to fetch projects' },
      { status: 500 }
    );
  }
}


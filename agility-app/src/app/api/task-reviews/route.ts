import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/db';

type ReviewStatus = 'PASS' | 'WARN' | 'FAIL';

const VALID_STATUSES: ReviewStatus[] = ['PASS', 'WARN', 'FAIL'];

function normalizeStatus(status: string): ReviewStatus | null {
  const upper = status.toUpperCase() as ReviewStatus;
  return VALID_STATUSES.includes(upper) ? upper : null;
}

function formatFindings(findings: unknown): unknown[] {
  if (Array.isArray(findings)) {
    return findings;
  }

  if (findings && typeof findings === 'object') {
    return [findings];
  }

  return [];
}

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id || !session.user.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { taskId, status, summary, findings } = await req.json();

    if (!taskId || !status || !summary) {
      return NextResponse.json(
        { error: 'taskId, status, and summary are required' },
        { status: 400 },
      );
    }

    const normalizedStatus = normalizeStatus(status);
    if (!normalizedStatus) {
      return NextResponse.json(
        { error: `Invalid status. Expected one of ${VALID_STATUSES.join(', ')}` },
        { status: 400 },
      );
    }

    const task = await db.task.findUnique({
      where: { id: taskId },
    });

    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    const projectId = (task as { projectId?: string } | null)?.projectId;

    if (!projectId) {
      return NextResponse.json(
        { error: 'Task is missing project reference' },
        { status: 400 },
      );
    }

    const membership = await db.organizationMember.findFirst({
      where: {
        organization: {
          projects: {
            some: {
              id: projectId,
            },
          },
        },
        userId: session.user.id,
      },
      select: {
        id: true,
      },
    });

    const isMember = Boolean(membership);

    if (!isMember) {
      return NextResponse.json(
        { error: 'You do not have access to submit a review for this task' },
        { status: 403 },
      );
    }

    const review = await (db as any).taskReview.create({
      data: {
        taskId,
        developerId: session.user.id,
        status: normalizedStatus,
        summary: summary.trim(),
        findings: formatFindings(findings),
      },
      include: {
        developer: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
    });

    return NextResponse.json({ review });
  } catch (error) {
    console.error('[CREATE_TASK_REVIEW_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to create task review' },
      { status: 500 },
    );
  }
}

export async function GET(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id || !session.user.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const taskId = searchParams.get('taskId');
    const limitParam = searchParams.get('limit');
    const limit = limitParam ? Math.min(parseInt(limitParam, 10), 20) : 10;

    if (!taskId) {
      return NextResponse.json(
        { error: 'taskId query parameter is required' },
        { status: 400 },
      );
    }

    const task = await db.task.findUnique({
      where: { id: taskId },
    });

    if (!task) {
      return NextResponse.json({ error: 'Task not found' }, { status: 404 });
    }

    const projectId = (task as { projectId?: string } | null)?.projectId;

    if (!projectId) {
      return NextResponse.json(
        { error: 'Task is missing project reference' },
        { status: 400 },
      );
    }

    const membership = await db.organizationMember.findFirst({
      where: {
        organization: {
          projects: {
            some: {
              id: projectId,
            },
          },
        },
        userId: session.user.id,
      },
      select: {
        id: true,
      },
    });

    const isMember = Boolean(membership);

    if (!isMember) {
      return NextResponse.json(
        { error: 'You do not have access to view reviews for this task' },
        { status: 403 },
      );
    }

    const reviews = await (db as any).taskReview.findMany({
      where: { taskId },
      orderBy: { createdAt: 'desc' },
      take: limit,
      include: {
        developer: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
    });

    const formatted = reviews.map((review: (typeof reviews)[number]) => ({
      id: review.id,
      taskId: review.taskId,
      status: review.status,
      summary: review.summary,
      findings: formatFindings(review.findings),
      createdAt: review.createdAt,
      developer: review.developer,
    }));

    return NextResponse.json({ reviews: formatted });
  } catch (error) {
    console.error('[GET_TASK_REVIEWS_ERROR]', error);
    return NextResponse.json(
      { error: 'Failed to fetch task reviews' },
      { status: 500 },
    );
  }
}


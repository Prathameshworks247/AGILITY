import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { inviteCode } = await req.json();

    if (!inviteCode) {
      return NextResponse.json(
        { error: 'Invite code is required' },
        { status: 400 }
      );
    }

    // Normalize invite code (remove spaces, uppercase)
    const normalizedCode = inviteCode.toUpperCase().trim();

    // Find organization by invite code
    const organization = await prisma.organization.findUnique({
      where: { inviteCode: normalizedCode },
    });

    if (!organization) {
      return NextResponse.json(
        { error: 'Invalid invite code' },
        { status: 404 }
      );
    }

    // Get user
    const user = await prisma.user.findUnique({
      where: { email: session.user.email },
    });

    if (!user) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Check if user is already a member
    const existingMember = await prisma.organizationMember.findFirst({
      where: {
        organizationId: organization.id,
        userId: user.id,
      },
    });

    if (existingMember) {
      return NextResponse.json(
        { error: 'You are already a member of this organization' },
        { status: 400 }
      );
    }

    // Add user as a member (developer role)
    await prisma.organizationMember.create({
      data: {
        organizationId: organization.id,
        userId: user.id,
        role: 'member', // developers are regular members
      },
    });

    return NextResponse.json({
      message: 'Successfully joined organization',
      organization: {
        id: organization.id,
        name: organization.name,
        slug: organization.slug,
      },
    });
  } catch (error) {
    console.error('Error joining organization:', error);
    return NextResponse.json(
      { error: 'Failed to join organization' },
      { status: 500 }
    );
  }
}


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

    const { role } = await req.json();

    // Validate role
    if (!['scrumMaster', 'developer'].includes(role)) {
      return NextResponse.json(
        { error: 'Invalid role. Must be scrumMaster or developer' },
        { status: 400 }
      );
    }

    // Update user role
    const user = await prisma.user.update({
      where: { email: session.user.email },
      data: { role },
    });

    return NextResponse.json({ 
      message: 'Role updated successfully',
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
      }
    });
  } catch (error) {
    console.error('Error updating user role:', error);
    return NextResponse.json(
      { error: 'Failed to update role' },
      { status: 500 }
    );
  }
}


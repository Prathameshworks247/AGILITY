import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { db } from "@/lib/db";

// Generate random invite code
function generateInviteCode(): string {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 9; i++) {
    code += characters.charAt(Math.floor(Math.random() * characters.length));
    if ((i + 1) % 3 === 0 && i < 8) {
      code += '-';
    }
  }
  return code;
}

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { name, description } = body;

    if (!name) {
      return NextResponse.json(
        { error: "Organization name is required" },
        { status: 400 }
      );
    }

    // Create slug from name
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    // Check if slug already exists
    const existingOrg = await db.organization.findUnique({
      where: { slug },
    });

    if (existingOrg) {
      return NextResponse.json(
        { error: "An organization with this name already exists" },
        { status: 400 }
      );
    }

    // Generate unique invite code
    let inviteCode = generateInviteCode();
    let codeExists = await db.organization.findUnique({
      where: { inviteCode },
    });
    
    // Regenerate if code already exists (very unlikely)
    while (codeExists) {
      inviteCode = generateInviteCode();
      codeExists = await db.organization.findUnique({
        where: { inviteCode },
      });
    }

    // Create organization
    const organization = await db.organization.create({
      data: {
        name,
        slug,
        description,
        inviteCode,
        members: {
          create: {
            userId: session.user.id,
            role: "owner",
          },
        },
      },
      include: {
        members: true,
      },
    });

    return NextResponse.json(
      {
        organization: {
          id: organization.id,
          name: organization.name,
          slug: organization.slug,
          inviteCode: organization.inviteCode,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("[CREATE_ORG_ERROR]", error);
    return NextResponse.json(
      { error: "Something went wrong" },
      { status: 500 }
    );
  }
}

// Get user's organizations
export async function GET(request: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const organizations = await db.organization.findMany({
      where: {
        members: {
          some: {
            userId: session.user.id,
          },
        },
      },
      select: {
        id: true,
        name: true,
        slug: true,
        description: true,
        inviteCode: true,
        createdAt: true,
        updatedAt: true,
        members: {
          where: {
            userId: session.user.id,
          },
          select: {
            role: true,
          },
        },
        _count: {
          select: {
            members: true,
            projects: true,
          },
        },
      },
    });

    return NextResponse.json({ organizations });
  } catch (error) {
    console.error("[GET_ORGS_ERROR]", error);
    return NextResponse.json(
      { error: "Something went wrong" },
      { status: 500 }
    );
  }
}


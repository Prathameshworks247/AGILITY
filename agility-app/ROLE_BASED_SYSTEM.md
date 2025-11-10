# Role-Based System Guide

## Overview

The Agility platform now supports two distinct user roles, each with different capabilities and dashboards:

1. **Scrum Master** - Manages organizations, projects, sprints, and teams
2. **Developer** - Views and updates assigned tasks

## User Flow

### First-Time Sign-Up

1. User registers via sign-up page
2. After registration, redirected to `/create-org`
3. User selects their role:
   - **Scrum Master** → Create organization flow
   - **Developer** → Join organization flow

### Scrum Master Flow

1. **Select Role**: Choose "Scrum Master" option
2. **Create Organization**: 
   - Enter organization name and description
   - System generates unique invite code (format: ABC-123-XYZ)
3. **Success Screen**:
   - View organization details
   - Copy invite code to share with developers
   - Navigate to Scrum Master dashboard

### Developer Flow

1. **Select Role**: Choose "Developer" option
2. **Join Organization**:
   - Enter invite code received from Scrum Master
   - System validates code and adds user to organization
3. **Developer Dashboard**:
   - View all assigned tasks
   - See task statistics
   - Update task status

## Dashboards

### Scrum Master Dashboard (`/dashboard/[orgSlug]`)

**Features:**
- Organization overview
- Project management
- Sprint planning and tracking
- Team member management
- Analytics and reports
- Burndown charts
- Velocity tracking

**Access:**
- Only Scrum Masters
- Must be organization owner or admin

### Developer Dashboard (`/developer-dashboard`)

**Features:**
- Personal task list
- Task statistics (Total, To Do, In Progress, Done)
- Task details (title, description, status, priority, story points)
- Project and sprint information for each task
- Quick navigation to task details

**Access:**
- Only Developers
- Shows tasks from all organizations they're part of

## API Routes

### User Management

#### Set User Role
```
POST /api/user/role
Body: { "role": "scrumMaster" | "developer" }
```
Sets the user's role in the system.

#### Get User Profile
```
GET /api/user/profile
Returns: { "user": { "id", "name", "email", "role", "image" } }
```
Gets the current user's profile information.

#### Get User Tasks
```
GET /api/tasks/my-tasks
Returns: { "tasks": [...] }
```
Gets all tasks assigned to the current user (for developers).

### Organization Management

#### Create Organization
```
POST /api/organizations
Body: { "name": string, "description"?: string }
Returns: { "organization": { "id", "name", "slug", "inviteCode" } }
```
Creates a new organization with a unique invite code.

#### Join Organization
```
POST /api/organizations/join
Body: { "inviteCode": string }
Returns: { "message": string, "organization": {...} }
```
Allows a developer to join an organization using an invite code.

#### Get Organizations
```
GET /api/organizations
Returns: { "organizations": [...] }
```
Gets all organizations the user is a member of.

## Database Schema Updates

### User Model
```prisma
model User {
  // ... other fields
  role String? // "scrumMaster" | "developer" (null until selected)
}
```

### Organization Model
```prisma
model Organization {
  // ... other fields
  inviteCode String @unique // Format: ABC-123-XYZ
}
```

## Sign-In Flow Logic

When a user signs in, the system:

1. Authenticates credentials
2. Fetches user profile to check role
3. Routes based on role:
   - **No role** → `/create-org` (role selection)
   - **Developer** → `/developer-dashboard`
   - **Scrum Master with orgs** → `/dashboard/[firstOrgSlug]`
   - **Scrum Master without orgs** → `/create-org` (create organization)

## Invite Code System

### Format
- 9 characters: `ABC-123-XYZ`
- Alphanumeric (A-Z, 0-9)
- Hyphenated for readability

### Generation
- Automatically generated when organization is created
- Guaranteed to be unique
- Can be regenerated if collision occurs (very rare)

### Usage
- Scrum Master shares code with developers
- Developers enter code to join organization
- Code is case-insensitive (automatically uppercase)
- Invalid codes show error message

## Protected Routes

All the following routes require authentication:

- `/dashboard/:path*` - Scrum Master dashboard
- `/developer-dashboard` - Developer dashboard
- `/project/:path*` - Project pages
- `/sprint/:path*` - Sprint pages
- `/create-org` - Role selection and org creation/join

## UI Components

### Role Selection Cards

Two interactive cards showing:
- **Scrum Master**:
  - Crown icon
  - Features: Create orgs, manage projects, track progress
  - Click to select
  
- **Developer**:
  - Users icon
  - Features: Join teams, view tasks, update status
  - Click to select

### Organization Success Screen

Displays after Scrum Master creates organization:
- Organization name
- Large, copyable invite code
- Button to navigate to dashboard
- Visual confirmation (green checkmark)

### Developer Task Cards

Each task shows:
- Status icon (circle, clock, checkmark)
- Title and description
- Status badge
- Priority badge
- Story points
- Project name
- Sprint name
- View button

## Best Practices

### For Scrum Masters
1. Create organization with clear, descriptive name
2. Copy invite code immediately after creation
3. Share invite code securely with team members
4. Keep track of which codes belong to which organization
5. Consider documenting invite codes in secure location

### For Developers
1. Request invite code from your Scrum Master
2. Enter code exactly as provided (case doesn't matter)
3. Verify you've joined the correct organization
4. Check developer dashboard for assigned tasks
5. Update task status regularly

## Future Enhancements

Potential improvements:
- [ ] Ability to regenerate invite codes
- [ ] Invite code expiration
- [ ] Email-based invitations
- [ ] Multiple roles per user
- [ ] Organization transfer between Scrum Masters
- [ ] Developer metrics and analytics
- [ ] Task filtering and search in developer dashboard
- [ ] Real-time task updates
- [ ] Notification system

## Troubleshooting

### Issue: Invalid invite code
**Solution**: Verify code with Scrum Master, ensure no spaces or typos

### Issue: Already a member error
**Solution**: User is already in the organization, go to dashboard

### Issue: Role not set after sign-up
**Solution**: Clear cookies and sign in again, system will prompt for role

### Issue: Wrong dashboard after sign-in
**Solution**: Role may be incorrect, contact administrator to update role

### Issue: No tasks showing in developer dashboard
**Solution**: 
- Verify you've joined an organization
- Check with Scrum Master if tasks have been assigned
- Ensure you're in active sprints

## Testing the System

### Test Scrum Master Flow
1. Create new account
2. Select "Scrum Master" role
3. Create organization "Test Org"
4. Copy invite code
5. Verify dashboard loads with org name

### Test Developer Flow
1. Create new account
2. Select "Developer" role
3. Enter invite code from test org
4. Verify developer dashboard loads
5. Check that no tasks show (initially empty)

### Test Sign-In Redirects
1. Sign out
2. Sign in as Scrum Master → Should redirect to org dashboard
3. Sign out
4. Sign in as Developer → Should redirect to developer dashboard


"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Plus, Settings, Users, Copy, CheckCircle2 } from "lucide-react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { useSession } from "next-auth/react";

interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  _count: {
    sprints: number;
    tasks: number;
    members: number;
  };
}

interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  inviteCode: string;
}

interface Member {
  id: string;
  role: string;
  user: {
    id: string;
    name?: string;
    email: string;
    image?: string;
    role?: string;
  };
}

const OrganizationDashboard = () => {
  const { orgId } = useParams();
  const { data: session } = useSession();
  
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
  });

  useEffect(() => {
    if (orgId) {
      fetchDashboardData();
    }
  }, [orgId]);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      // Fetch organization details
      const orgResponse = await fetch(`/api/organizations`);
      const orgData = await orgResponse.json();
      
      console.log('Organizations fetched:', orgData);
      
      const currentOrg = orgData.organizations?.find((o: any) => o.slug === orgId);
      console.log('Current org:', currentOrg);
      
      if (currentOrg) {
        setOrganization(currentOrg);
        
        // Fetch projects
        const projectsResponse = await fetch(`/api/projects?organizationId=${currentOrg.id}`);
        const projectsData = await projectsResponse.json();
        console.log('Projects fetched:', projectsData);
        setProjects(projectsData.projects || []);
        
        // Fetch members
        const membersResponse = await fetch(`/api/organizations/${currentOrg.id}/members`);
        const membersData = await membersResponse.json();
        console.log('Members fetched:', membersData);
        setMembers(membersData.members || []);
      } else {
        console.error('Organization not found with slug:', orgId);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!organization) return;
    
    setIsCreating(true);
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newProject,
          organizationId: organization.id,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to create project');
      }

      toast.success('Project created successfully!');
      setCreateDialogOpen(false);
      setNewProject({ name: "", description: "" });
      fetchDashboardData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const copyInviteCode = () => {
    if (organization?.inviteCode) {
      navigator.clipboard.writeText(organization.inviteCode);
      toast.success('Invite code copied to clipboard!');
    }
  };

  const getDevelopers = () => members.filter(m => m.user.role === 'developer');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Organization not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">{organization.name}</h1>
              <p className="text-sm text-muted-foreground">{organization.description || 'Organization Dashboard'}</p>
            </div>
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback>
                  {session?.user?.name?.charAt(0)?.toUpperCase() || 'SM'}
                </AvatarFallback>
              </Avatar>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Organization Info & Invite Code */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Team Members</CardTitle>
              <CardDescription>{members.length} total members</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Scrum Masters</span>
                  <span className="font-semibold">{members.filter(m => m.user.role === 'scrumMaster').length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Developers</span>
                  <span className="font-semibold">{getDevelopers().length}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Invite Code</CardTitle>
              <CardDescription>Share this code with developers to join</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  value={organization.inviteCode}
                  readOnly
                  className="text-center text-lg tracking-wider font-mono font-bold"
                />
                <Button size="icon" variant="outline" onClick={copyInviteCode}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Team Members List */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Your Team</CardTitle>
            <CardDescription>All members of this organization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {members.map((member) => (
                <div key={member.id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>
                        {member.user.name?.charAt(0)?.toUpperCase() || member.user.email.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{member.user.name || member.user.email}</p>
                      <p className="text-sm text-muted-foreground">{member.user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={member.user.role === 'scrumMaster' ? 'default' : 'secondary'}>
                      {member.user.role === 'scrumMaster' ? 'Scrum Master' : 'Developer'}
                    </Badge>
                    <Badge variant="outline">
                      {member.role === 'owner' ? 'Owner' : member.role}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Projects Section */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-foreground mb-2">Your Projects</h2>
          <p className="text-muted-foreground">Select a project to view details and manage sprints</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Create New Project Card */}
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
          <Card className="border-dashed border-2 hover:border-primary transition-colors cursor-pointer">
            <CardHeader className="text-center py-12">
              <div className="mx-auto rounded-full bg-primary/10 w-16 h-16 flex items-center justify-center mb-4">
                <Plus className="h-8 w-8 text-primary" />
              </div>
              <CardTitle>Create New Project</CardTitle>
              <CardDescription>Start a new project with your team</CardDescription>
            </CardHeader>
          </Card>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
                <DialogDescription>
                  Add a new project to your organization
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateProject}>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="name">Project Name</Label>
                    <Input
                      id="name"
                      value={newProject.name}
                      onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                      placeholder="e.g., Mobile App v2"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={newProject.description}
                      onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                      placeholder="Brief description of the project..."
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter className="mt-6">
                  <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isCreating}>
                    {isCreating ? "Creating..." : "Create Project"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>

          {/* Project Cards */}
          {projects.map((project) => (
            <Link key={project.id} href={`/project/${project.slug}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                  <CardDescription>{project.description || 'No description'}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Total Sprints</span>
                      <span className="font-semibold text-foreground">{project._count.sprints}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Total Tasks</span>
                      <span className="font-semibold text-foreground">{project._count.tasks}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        Team Members
                      </span>
                      <span className="font-semibold text-foreground">{project._count.members}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {projects.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No projects yet. Create your first project to get started!</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default OrganizationDashboard;

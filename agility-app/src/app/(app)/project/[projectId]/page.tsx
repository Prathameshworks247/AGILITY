"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Calendar, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

interface Sprint {
  id: string;
  name: string;
  goal?: string;
  status: string;
  startDate: string;
  endDate: string;
  plannedPoints: number;
  completedPoints: number;
  _count: {
    tasks: number;
  };
}

interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  organization: {
    name: string;
    slug: string;
  };
}

const ProjectDashboard = () => {
  const { projectId } = useParams();
  const router = useRouter();
  
  const [project, setProject] = useState<Project | null>(null);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  const [newSprint, setNewSprint] = useState({
    name: "",
    goal: "",
    startDate: "",
    endDate: "",
    plannedPoints: "",
  });

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId]);

  const fetchProjectData = async () => {
    setIsLoading(true);
    try {
      // First get all projects to find the one with this slug
      const orgsResponse = await fetch('/api/organizations');
      const orgsData = await orgsResponse.json();
      
      let projectData = null;
      for (const org of orgsData.organizations || []) {
        const projectsResponse = await fetch(`/api/projects?organizationId=${org.id}`);
        const projectsData = await projectsResponse.json();
        projectData = projectsData.projects?.find((p: any) => p.slug === projectId);
        
        if (projectData) {
          projectData.organization = { name: org.name, slug: org.slug };
          break;
        }
      }
      
      if (projectData) {
        setProject(projectData);
        
        // Fetch sprints
        const sprintsResponse = await fetch(`/api/sprints?projectId=${projectData.id}`);
        const sprintsData = await sprintsResponse.json();
        setSprints(sprintsData.sprints || []);
      }
    } catch (error) {
      console.error('Error fetching project data:', error);
      toast.error('Failed to load project data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSprint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;
    
    setIsCreating(true);
    try {
      const response = await fetch('/api/sprints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newSprint,
          projectId: project.id,
          plannedPoints: parseInt(newSprint.plannedPoints) || 0,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to create sprint');
      }

      toast.success('Sprint created successfully!');
      setCreateDialogOpen(false);
      setNewSprint({ name: "", goal: "", startDate: "", endDate: "", plannedPoints: "" });
      fetchProjectData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to create sprint');
    } finally {
      setIsCreating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'default';
      case 'COMPLETED':
        return 'secondary';
      case 'PLANNING':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getDaysRemaining = (endDate: string) => {
    const now = new Date();
    const end = new Date(endDate);
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diff < 0) return 'Ended';
    if (diff === 0) return 'Ends today';
    if (diff === 1) return '1 day remaining';
    return `${diff} days remaining`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Project not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-muted-foreground mb-1">
                <Link 
                  href={`/dashboard/${project.organization.slug}`} 
                  className="hover:text-foreground"
                >
                  {project.organization.name}
                </Link> / {project.name}
              </div>
              <h1 className="text-2xl font-bold text-foreground">{project.name}</h1>
              {project.description && (
                <p className="text-sm text-muted-foreground mt-1">{project.description}</p>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Sprints Section */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground mb-2">Sprints</h2>
            <p className="text-muted-foreground">Manage and track your project sprints</p>
          </div>
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Sprint
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Create New Sprint</DialogTitle>
                <DialogDescription>
                  Add a new sprint to {project.name}
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateSprint}>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="name">Sprint Name</Label>
                    <Input
                      id="name"
                      value={newSprint.name}
                      onChange={(e) => setNewSprint({ ...newSprint, name: e.target.value })}
                      placeholder="e.g., Sprint 1"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="goal">Sprint Goal</Label>
                    <Textarea
                      id="goal"
                      value={newSprint.goal}
                      onChange={(e) => setNewSprint({ ...newSprint, goal: e.target.value })}
                      placeholder="What do you want to achieve in this sprint?"
                      rows={2}
                    />
                        </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="startDate">Start Date</Label>
                      <Input
                        id="startDate"
                        type="date"
                        value={newSprint.startDate}
                        onChange={(e) => setNewSprint({ ...newSprint, startDate: e.target.value })}
                        required
                      />
                      </div>
                    <div>
                      <Label htmlFor="endDate">End Date</Label>
                      <Input
                        id="endDate"
                        type="date"
                        value={newSprint.endDate}
                        onChange={(e) => setNewSprint({ ...newSprint, endDate: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="plannedPoints">Planned Story Points</Label>
                    <Input
                      id="plannedPoints"
                      type="number"
                      value={newSprint.plannedPoints}
                      onChange={(e) => setNewSprint({ ...newSprint, plannedPoints: e.target.value })}
                      placeholder="0"
                      min="0"
                    />
                  </div>
                </div>
                <DialogFooter className="mt-6">
                  <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isCreating}>
                    {isCreating ? "Creating..." : "Create Sprint"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
                </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sprints.map((sprint) => (
                    <Link key={sprint.id} href={`/project/${projectId}/sprint/${sprint.id}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                        <div className="flex items-center justify-between mb-2">
                    <CardTitle>{sprint.name}</CardTitle>
                    <Badge variant={getStatusColor(sprint.status)}>
                            {sprint.status}
                          </Badge>
                        </div>
                  <CardDescription>{sprint.goal || 'No goal set'}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        Duration
                      </span>
                      <span className="font-semibold">
                        {formatDate(sprint.startDate)} - {formatDate(sprint.endDate)}
                      </span>
                    </div>
                    {sprint.status === 'ACTIVE' && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground flex items-center gap-2">
                          <Clock className="h-4 w-4" />
                          Time
                        </span>
                        <span className="font-semibold">{getDaysRemaining(sprint.endDate)}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Tasks</span>
                      <span className="font-semibold">{sprint._count.tasks}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Story Points</span>
                      <span className="font-semibold">
                        {sprint.completedPoints} / {sprint.plannedPoints}
                      </span>
                    </div>
                    {sprint.plannedPoints > 0 && (
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div 
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{ width: `${(sprint.completedPoints / sprint.plannedPoints) * 100}%` }}
                        />
                      </div>
                    )}
                </div>
              </CardContent>
            </Card>
            </Link>
          ))}
        </div>

        {sprints.length === 0 && (
          <Card>
            <CardContent className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Plus className="h-8 w-8 text-primary" />
              </div>
              <p className="text-lg font-medium mb-2">No sprints yet</p>
              <p className="text-sm text-muted-foreground mb-4">
                Create your first sprint to start tracking work
              </p>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create First Sprint
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default ProjectDashboard;

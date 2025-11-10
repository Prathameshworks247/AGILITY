"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar, Plus, Edit } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  storyPoints?: number;
  assignee?: {
    id: string;
    name?: string;
    email: string;
  };
  sprint?: {
    id: string;
    name: string;
  };
}

interface Sprint {
  id: string;
  name: string;
  goal?: string;
  status: string;
  startDate: string;
  endDate: string;
  plannedPoints: number;
  completedPoints: number;
  project: {
    name: string;
    slug: string;
  };
}

interface Member {
  id: string;
  user: {
    id: string;
    name?: string;
    email: string;
  };
}

const SprintDashboard = () => {
  const { projectId, sprintId } = useParams();
  
  const [sprint, setSprint] = useState<Sprint | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
const [projectInfo, setProjectInfo] = useState<{ id: string; orgId: string; name: string; slug: string } | null>(null);
  
  const [newTask, setNewTask] = useState({
    title: "",
    description: "",
    assigneeId: "",
    priority: "MEDIUM",
    storyPoints: "",
  });

  useEffect(() => {
    if (projectId && sprintId) {
      fetchSprintData();
    }
  }, [projectId, sprintId]);

  const fetchSprintData = async () => {
    setIsLoading(true);
    try {
      // Fetch organizations and projects to find current project
      const orgsResponse = await fetch('/api/organizations');
      const orgsData = await orgsResponse.json();

      let foundProject: any = null;
      let foundOrgId: string | null = null;

      for (const org of orgsData.organizations || []) {
        const projectsResponse = await fetch(`/api/projects?organizationId=${org.id}`);
        const projectsData = await projectsResponse.json();
        const project = projectsData.projects?.find((p: any) => p.slug === projectId);

        if (project) {
          foundProject = project;
          foundOrgId = org.id;
          break;
        }
      }

      if (!foundProject || !foundOrgId) {
        throw new Error('Project not found');
      }

      setProjectInfo({
        id: foundProject.id,
        orgId: foundOrgId,
        name: foundProject.name,
        slug: foundProject.slug,
      });

      // Fetch sprint details
      const sprintsResponse = await fetch(`/api/sprints?projectId=${foundProject.id}`);
      const sprintsData = await sprintsResponse.json();
      const sprintData = sprintsData.sprints?.find((s: any) => s.id === sprintId);

      if (sprintData) {
        sprintData.project = {
          id: foundProject.id,
          name: foundProject.name,
          slug: foundProject.slug,
        };
        setSprint(sprintData);
      } else {
        setSprint(null);
      }

      // Fetch members for assignment
      const membersResponse = await fetch(`/api/organizations/${foundOrgId}/members`);
      const membersData = await membersResponse.json();
      setMembers(membersData.members || []);

      // Fetch tasks for sprint
      const tasksResponse = await fetch(`/api/tasks?sprintId=${sprintId}`);
      const tasksData = await tasksResponse.json();
      setTasks(tasksData.tasks || []);
    } catch (error) {
      console.error('Error fetching sprint data:', error);
      toast.error('Failed to load sprint data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sprint || !projectInfo) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newTask,
          projectId: projectInfo.id,
          sprintId: sprint.id,
          storyPoints: newTask.storyPoints ? parseInt(newTask.storyPoints, 10) : null,
          assigneeId: newTask.assigneeId || null,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to create task');
      }

      toast.success('Task created successfully!');
      setCreateDialogOpen(false);
      setNewTask({ title: "", description: "", assigneeId: "", priority: "MEDIUM", storyPoints: "" });
      fetchSprintData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to create task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>) => {
    try {
      const response = await fetch('/api/tasks', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskId,
          ...updates,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to update task');
      }

      toast.success('Task updated successfully!');
      fetchSprintData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to update task');
    }
  };

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setNewTask({
      title: task.title,
      description: task.description || "",
      assigneeId: task.assignee?.id || "",
      priority: task.priority,
      storyPoints: task.storyPoints?.toString() || "",
    });
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    
    setIsSubmitting(true);
    try {
      await handleUpdateTask(selectedTask.id, {
        title: newTask.title,
        description: newTask.description,
        assigneeId: newTask.assigneeId || null,
        priority: newTask.priority,
        storyPoints: parseInt(newTask.storyPoints) || null,
      } as any);
      
      setEditDialogOpen(false);
      setSelectedTask(null);
      setNewTask({ title: "", description: "", assigneeId: "", priority: "MEDIUM", storyPoints: "" });
    } catch (error) {
      // Error already handled in handleUpdateTask
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'destructive';
      case 'MEDIUM':
        return 'default';
      case 'LOW':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'TODO':
        return 'secondary';
      case 'IN_PROGRESS':
        return 'default';
      case 'IN_REVIEW':
        return 'outline';
      case 'DONE':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const groupedTasks = {
    TODO: tasks.filter(t => t.status === 'TODO'),
    IN_PROGRESS: tasks.filter(t => t.status === 'IN_PROGRESS'),
    IN_REVIEW: tasks.filter(t => t.status === 'IN_REVIEW'),
    DONE: tasks.filter(t => t.status === 'DONE'),
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading sprint...</p>
        </div>
      </div>
    );
  }

  const TaskColumn = ({ title, tasks: columnTasks, status }: { title: string; tasks: Task[]; status: string }) => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-foreground">{title}</h3>
        <Badge variant="outline">{columnTasks.length}</Badge>
      </div>
      <div className="space-y-2">
        {columnTasks.map((task) => (
          <Card key={task.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-4">
              <div className="space-y-2">
                <div className="flex items-start justify-between">
                  <h4 className="font-medium text-sm">{task.title}</h4>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6"
                    onClick={() => handleEditTask(task)}
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                </div>
                {task.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">{task.description}</p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant={getPriorityColor(task.priority)} className="text-xs">
                    {task.priority}
                  </Badge>
                  {task.storyPoints && (
                    <Badge variant="outline" className="text-xs">{task.storyPoints} pts</Badge>
                  )}
                  {task.assignee && (
                    <div className="flex items-center gap-1">
                      <Avatar className="h-5 w-5">
                        <AvatarFallback className="text-xs">
                          {task.assignee.name?.charAt(0)?.toUpperCase() || task.assignee.email.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-xs text-muted-foreground">
                        {task.assignee.name || task.assignee.email}
                      </span>
                    </div>
                  )}
                </div>
                {status !== 'DONE' && (
                  <Select
                    value={task.status}
                    onValueChange={(value) => handleUpdateTask(task.id, { status: value })}
                  >
                    <SelectTrigger className="h-7 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TODO">To Do</SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="IN_REVIEW">In Review</SelectItem>
                      <SelectItem value="DONE">Done</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              {sprint && (
                <div className="text-sm text-muted-foreground mb-1">
                  <Link href={`/project/${projectId}`} className="hover:text-foreground">
                    {sprint.project.name}
                  </Link> / {sprint.name}
                </div>
              )}
              <h1 className="text-2xl font-bold text-foreground">{sprint?.name || 'Sprint'}</h1>
              {sprint?.goal && (
                <p className="text-sm text-muted-foreground mt-1">{sprint.goal}</p>
              )}
            </div>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Task
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Create New Task</DialogTitle>
                  <DialogDescription>
                    Add a new task to {sprint?.name}
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateTask}>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="title">Task Title</Label>
                      <Input
                        id="title"
                        value={newTask.title}
                        onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                        placeholder="e.g., Implement login feature"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="description">Description</Label>
                      <Textarea
                        id="description"
                        value={newTask.description}
                        onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                        placeholder="Describe the task..."
                        rows={3}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="priority">Priority</Label>
                        <Select
                          value={newTask.priority}
                          onValueChange={(value) => setNewTask({ ...newTask, priority: value })}
                        >
                          <SelectTrigger id="priority">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="LOW">Low</SelectItem>
                            <SelectItem value="MEDIUM">Medium</SelectItem>
                            <SelectItem value="HIGH">High</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="storyPoints">Story Points</Label>
                        <Input
                          id="storyPoints"
                          type="number"
                          value={newTask.storyPoints}
                          onChange={(e) => setNewTask({ ...newTask, storyPoints: e.target.value })}
                          placeholder="0"
                          min="0"
                        />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="assignee">Assign To</Label>
                      <Select
                        value={newTask.assigneeId || "UNASSIGNED"}
                        onValueChange={(value) =>
                          setNewTask({
                            ...newTask,
                            assigneeId: value === "UNASSIGNED" ? "" : value,
                          })
                        }
                      >
                        <SelectTrigger id="assignee">
                          <SelectValue placeholder="Select team member" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="UNASSIGNED">Unassigned</SelectItem>
                          {members.filter(m => m.user).map((member) => (
                            <SelectItem key={member.user.id} value={member.user.id}>
                              {member.user.name || member.user.email}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter className="mt-6">
                    <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? "Creating..." : "Create Task"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            {/* Edit Task Dialog */}
            <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Edit Task</DialogTitle>
                  <DialogDescription>
                    Update task details
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSaveEdit}>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="edit-title">Task Title</Label>
                      <Input
                        id="edit-title"
                        value={newTask.title}
                        onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                        placeholder="e.g., Implement login feature"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="edit-description">Description</Label>
                      <Textarea
                        id="edit-description"
                        value={newTask.description}
                        onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                        placeholder="Describe the task..."
                        rows={3}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="edit-priority">Priority</Label>
                        <Select
                          value={newTask.priority}
                          onValueChange={(value) => setNewTask({ ...newTask, priority: value })}
                        >
                          <SelectTrigger id="edit-priority">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="LOW">Low</SelectItem>
                            <SelectItem value="MEDIUM">Medium</SelectItem>
                            <SelectItem value="HIGH">High</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="edit-storyPoints">Story Points</Label>
                        <Input
                          id="edit-storyPoints"
                          type="number"
                          value={newTask.storyPoints}
                          onChange={(e) => setNewTask({ ...newTask, storyPoints: e.target.value })}
                          placeholder="0"
                          min="0"
                        />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="edit-assignee">Assign To</Label>
                      <Select
                        value={newTask.assigneeId || "UNASSIGNED"}
                        onValueChange={(value) =>
                          setNewTask({
                            ...newTask,
                            assigneeId: value === "UNASSIGNED" ? "" : value,
                          })
                        }
                      >
                        <SelectTrigger id="edit-assignee">
                          <SelectValue placeholder="Select team member" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="UNASSIGNED">Unassigned</SelectItem>
                          {members.filter(m => m.user).map((member) => (
                            <SelectItem key={member.user.id} value={member.user.id}>
                              {member.user.name || member.user.email}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter className="mt-6">
                    <Button type="button" variant="outline" onClick={() => {
                      setEditDialogOpen(false);
                      setSelectedTask(null);
                      setNewTask({ title: "", description: "", assigneeId: "", priority: "MEDIUM", storyPoints: "" });
                    }}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? "Saving..." : "Save Changes"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </header>

      {/* Sprint Info */}
      {sprint && (
        <div className="border-b bg-card">
          <div className="container mx-auto px-6 py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Duration
                </div>
                <div className="text-sm font-semibold text-foreground">
                  {formatDate(sprint.startDate)} - {formatDate(sprint.endDate)}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Status</div>
                <Badge variant={getStatusColor(sprint.status)}>{sprint.status}</Badge>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total Tasks</div>
                <div className="text-2xl font-bold">{tasks.length}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Story Points</div>
                <div className="text-2xl font-bold">
                  {sprint.completedPoints} / {sprint.plannedPoints}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="container mx-auto px-6 py-8">
        {tasks.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Plus className="h-8 w-8 text-primary" />
              </div>
              <p className="text-lg font-medium mb-2">No tasks yet</p>
              <p className="text-sm text-muted-foreground mb-4">
                Create your first task to start working
              </p>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create First Task
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <TaskColumn title="To Do" tasks={groupedTasks.TODO} status="TODO" />
            <TaskColumn title="In Progress" tasks={groupedTasks.IN_PROGRESS} status="IN_PROGRESS" />
            <TaskColumn title="In Review" tasks={groupedTasks.IN_REVIEW} status="IN_REVIEW" />
            <TaskColumn title="Done" tasks={groupedTasks.DONE} status="DONE" />
          </div>
        )}
      </main>
    </div>
  );
};

export default SprintDashboard;

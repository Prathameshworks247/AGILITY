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

interface TaskReviewSummary {
  id: string;
  status: string;
  summary: string;
  findings: unknown[];
  createdAt: string;
  developer?: {
    id: string;
    name?: string | null;
    email: string;
  } | null;
}

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
  latestReview?: TaskReviewSummary | null;
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
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewTask, setReviewTask] = useState<Task | null>(null);
  const [reviewHistory, setReviewHistory] = useState<TaskReviewSummary[]>([]);
  const [isLoadingReviews, setIsLoadingReviews] = useState(false);
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

  const handleViewReview = async (task: Task) => {
    setReviewTask(task);
    setReviewDialogOpen(true);
    setIsLoadingReviews(true);
    try {
      const response = await fetch(`/api/task-reviews?taskId=${task.id}&limit=10`);
      if (!response.ok) {
        throw new Error('Failed to fetch review history');
      }
      const data = await response.json();
      setReviewHistory(data.reviews || []);
    } catch (error) {
      console.error('Error fetching task reviews:', error);
      toast.error('Failed to load AI review history');
      setReviewHistory([]);
    } finally {
      setIsLoadingReviews(false);
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

  const getReviewBadgeVariant = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'secondary';
      case 'WARN':
        return 'default';
      case 'FAIL':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getReviewStatusLabel = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'Pass';
      case 'WARN':
        return 'Warnings';
      case 'FAIL':
        return 'Requires Attention';
      default:
        return status;
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

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const diff = Date.now() - date.getTime();
    const minutes = Math.round(diff / (1000 * 60));

    if (minutes <= 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;

    const days = Math.round(hours / 24);
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
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
        {columnTasks.map((task) => {
          const latestReview = task.latestReview;
          return (
            <Card key={task.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-sm">{task.title}</h4>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(task.id);
                          toast.success('Task ID copied to clipboard!');
                        }}
                        className="text-[10px] text-muted-foreground hover:text-foreground font-mono mt-1 flex items-center gap-1 group"
                        title="Click to copy Task ID"
                      >
                        <span className="truncate max-w-[200px]">ID: {task.id}</span>
                        <svg className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </button>
                    </div>
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
                  {latestReview && (
                    <div className="space-y-2 rounded-md border bg-muted/40 p-2">
                      <div className="flex items-center justify-between">
                        <Badge variant={getReviewBadgeVariant(latestReview.status)}>
                          AI Review: {getReviewStatusLabel(latestReview.status)}
                        </Badge>
                        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                          {formatRelativeTime(latestReview.createdAt)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">{latestReview.summary}</p>
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>
                          {Array.isArray(latestReview.findings)
                            ? `${latestReview.findings.length} finding${latestReview.findings.length === 1 ? '' : 's'}`
                            : '0 findings'}
                        </span>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewReview(task);
                          }}
                        >
                          View details
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
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
                    {selectedTask && (
                      <div className="rounded-md border bg-muted/40 p-3">
                        <Label className="text-xs text-muted-foreground">Task ID (for VS Code Extension)</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="flex-1 text-xs font-mono bg-background px-2 py-1 rounded border truncate">
                            {selectedTask.id}
                          </code>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              navigator.clipboard.writeText(selectedTask.id);
                              toast.success('Task ID copied! Use it in VS Code extension.');
                            }}
                          >
                            Copy ID
                          </Button>
                        </div>
                      </div>
                    )}
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

            {/* Review History Dialog */}
            <Dialog
              open={reviewDialogOpen}
              onOpenChange={(open) => {
                setReviewDialogOpen(open);
                if (!open) {
                  setReviewTask(null);
                  setReviewHistory([]);
                }
              }}
            >
              <DialogContent className="max-w-3xl">
                <DialogHeader>
                  <DialogTitle>AI Review History</DialogTitle>
                  <DialogDescription>
                    {reviewTask ? `Task: ${reviewTask.title}` : 'Recent AI feedback for this task'}
                  </DialogDescription>
                </DialogHeader>
                {isLoadingReviews ? (
                  <div className="py-10 text-center text-muted-foreground text-sm">
                    Loading review history...
                  </div>
                ) : reviewHistory.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground text-sm">
                    No AI review feedback available for this task yet.
                  </div>
                ) : (
                  <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-2">
                    {reviewHistory.map((review) => {
                      const findings = Array.isArray(review.findings) ? review.findings : [];
                      return (
                        <div key={review.id} className="space-y-2 rounded-lg border bg-muted/40 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <Badge variant={getReviewBadgeVariant(review.status)}>
                                AI Review: {getReviewStatusLabel(review.status)}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {formatRelativeTime(review.createdAt)}
                              </span>
                            </div>
                            {review.developer && (
                              <span className="text-xs text-muted-foreground">
                                by {review.developer.name || review.developer.email}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-foreground">{review.summary}</p>
                          {findings.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Findings ({findings.length})
                              </p>
                              <ul className="space-y-2">
                                {findings.map((finding, index) => {
                                  if (finding && typeof finding === 'object') {
                                    const data = finding as Record<string, any>;
                                    const severity = typeof data.severity === 'string' ? data.severity.toUpperCase() : null;
                                    return (
                                      <li key={index} className="space-y-1 rounded-md border bg-background p-3 text-xs text-muted-foreground">
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="font-medium text-foreground">
                                            {data.title || data.message || `Finding ${index + 1}`}
                                          </span>
                                          {severity && (
                                            <Badge
                                              variant={
                                                severity === 'HIGH'
                                                  ? 'destructive'
                                                  : severity === 'MEDIUM'
                                                  ? 'default'
                                                  : 'secondary'
                                              }
                                            >
                                              {severity}
                                            </Badge>
                                          )}
                                        </div>
                                        {data.message && <p>{data.message}</p>}
                                        {(data.filePath || data.startLine) && (
                                          <p className="text-[10px] uppercase tracking-wide">
                                            {data.filePath ? data.filePath : ''}
                                            {data.startLine
                                              ? ` • Line ${data.startLine}${data.endLine ? `-${data.endLine}` : ''}`
                                              : ''}
                                          </p>
                                        )}
                                      </li>
                                    );
                                  }

                                  return (
                                    <li key={index} className="rounded-md border bg-background p-3 text-xs text-muted-foreground">
                                      {String(finding)}
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setReviewDialogOpen(false)}>
                    Close
                  </Button>
                </DialogFooter>
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

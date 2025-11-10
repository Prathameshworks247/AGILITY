"use client";
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Users, Crown } from 'lucide-react';

const CreateOrganization = () => {
  const router = useRouter();
  const [step, setStep] = useState<'role' | 'create' | 'join' | 'success'>('role');
  const [selectedRole, setSelectedRole] = useState<'scrumMaster' | 'developer' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const [orgData, setOrgData] = useState({
    name: '',
    description: '',
  });

  const [joinCode, setJoinCode] = useState('');
  const [createdOrg, setCreatedOrg] = useState<{
    name: string;
    slug: string;
    inviteCode: string;
  } | null>(null);

  const handleRoleSelect = async (role: 'scrumMaster' | 'developer') => {
    setSelectedRole(role);
    
    // Update user role in database
    try {
      const response = await fetch('/api/user/role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      });

      if (!response.ok) {
        toast.error('Failed to set role');
        return;
      }

      if (role === 'scrumMaster') {
        setStep('create');
      } else {
        setStep('join');
      }
    } catch (error) {
      toast.error('Something went wrong');
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/organizations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orgData),
      });

      const data = await response.json();

      if (!response.ok) {
        toast.error(data.error || 'Failed to create organization');
        setIsLoading(false);
        return;
      }

      toast.success('Organization created successfully!');
      setCreatedOrg(data.organization);
      setStep('success');
      setIsLoading(false);
    } catch (error) {
      toast.error('Something went wrong. Please try again.');
      setIsLoading(false);
    }
  };

  const copyInviteCode = () => {
    if (createdOrg?.inviteCode) {
      navigator.clipboard.writeText(createdOrg.inviteCode);
      toast.success('Invite code copied to clipboard!');
    }
  };

  const handleJoinOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/organizations/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inviteCode: joinCode }),
      });

      const data = await response.json();

      if (!response.ok) {
        toast.error(data.error || 'Failed to join organization');
        setIsLoading(false);
        return;
      }

      toast.success('Joined organization successfully!');
      router.push(`/developer-dashboard`);
    } catch (error) {
      toast.error('Invalid invite code. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {/* Role Selection */}
      {step === 'role' && (
        <div className="w-full max-w-4xl">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2">Choose Your Role</h1>
            <p className="text-muted-foreground">Select how you want to use Agility</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Scrum Master Card */}
            <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => handleRoleSelect('scrumMaster')}>
              <CardHeader className="text-center">
                <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <Crown className="h-8 w-8 text-primary" />
                </div>
                <CardTitle>Scrum Master</CardTitle>
                <CardDescription>Manage teams and projects</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">Perfect for:</p>
                <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                  <li>Creating and managing organizations</li>
                  <li>Setting up projects and sprints</li>
                  <li>Tracking team progress</li>
                  <li>Managing team members</li>
                  <li>Viewing analytics and reports</li>
                </ul>
              </CardContent>
            </Card>

            {/* Developer Card */}
            <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => handleRoleSelect('developer')}>
              <CardHeader className="text-center">
                <div className="mx-auto w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                  <Users className="h-8 w-8 text-accent" />
                </div>
                <CardTitle>Developer</CardTitle>
                <CardDescription>Join a team and track tasks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">Perfect for:</p>
                <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                  <li>Joining existing organizations</li>
                  <li>Viewing assigned tasks</li>
                  <li>Updating task status</li>
                  <li>Tracking personal metrics</li>
                  <li>Collaborating with team</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Create Organization (Scrum Master) */}
      {step === 'create' && (
        <Card className="w-full max-w-2xl">
          <CardHeader>
            <CardTitle className="text-2xl">Create Your Organization</CardTitle>
            <CardDescription>
              Set up your organization to start managing projects and teams
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateOrg} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="org-name">Organization Name</Label>
                <Input
                  id="org-name"
                  type="text"
                  placeholder="Acme Inc."
                  value={orgData.name}
                  onChange={(e) => setOrgData({ ...orgData, name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="org-description">Description</Label>
                <Textarea
                  id="org-description"
                  placeholder="Tell us about your organization..."
                  value={orgData.description}
                  onChange={(e) => setOrgData({ ...orgData, description: e.target.value })}
                  rows={4}
                />
              </div>

              <div className="flex gap-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setStep('role')} 
                  className="flex-1"
                  disabled={isLoading}
                >
                  Back
                </Button>
                <Button type="submit" className="flex-1" disabled={isLoading}>
                  {isLoading ? "Creating..." : "Create Organization"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Join Organization (Developer) */}
      {step === 'join' && (
        <Card className="w-full max-w-2xl">
          <CardHeader>
            <CardTitle className="text-2xl">Join an Organization</CardTitle>
            <CardDescription>
              Enter the invite code provided by your Scrum Master
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleJoinOrg} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="invite-code">Invite Code</Label>
                <Input
                  id="invite-code"
                  type="text"
                  placeholder="ABC-123-XYZ"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  required
                  className="text-center text-xl tracking-wider font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  Ask your Scrum Master for the organization invite code
                </p>
              </div>

              <div className="flex gap-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setStep('role')} 
                  className="flex-1"
                  disabled={isLoading}
                >
                  Back
                </Button>
                <Button type="submit" className="flex-1" disabled={isLoading}>
                  {isLoading ? "Joining..." : "Join Organization"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Success - Show Invite Code (Scrum Master) */}
      {step === 'success' && createdOrg && (
        <Card className="w-full max-w-2xl">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
              <Crown className="h-8 w-8 text-green-500" />
            </div>
            <CardTitle className="text-2xl">Organization Created!</CardTitle>
            <CardDescription>
              Share this invite code with your team members
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Organization Name</Label>
              <p className="text-lg font-semibold">{createdOrg.name}</p>
            </div>

            <div className="space-y-2">
              <Label>Invite Code</Label>
              <div className="flex gap-2">
                <Input
                  value={createdOrg.inviteCode}
                  readOnly
                  className="text-center text-2xl tracking-wider font-mono font-bold"
                />
                <Button type="button" variant="outline" onClick={copyInviteCode}>
                  Copy
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Developers can use this code to join your organization
              </p>
            </div>

            <Button 
              onClick={() => router.push(`/dashboard/${createdOrg.slug}`)} 
              className="w-full"
            >
              Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CreateOrganization;

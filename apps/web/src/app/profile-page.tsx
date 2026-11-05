import { useMutation, useQuery } from '@tanstack/react-query';
import { CalendarDays, LogOut, Mail, ShieldCheck, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Badge, Button, Card, PageHeader, SectionHeading } from '@/components/ui';
import { fetchCurrentOwner, logout } from '@/lib/api';

export function ProfilePage() {
  const navigate = useNavigate();
  const ownerQuery = useQuery({ queryKey: ['current-owner'], queryFn: ({ signal }) => fetchCurrentOwner(signal) });
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => navigate('/login', { replace: true }) });
  const owner = ownerQuery.data;

  return <div className="space-y-8">
    <PageHeader eyebrow="Account" title="Profile" description="Manage your DocuMind identity and active workspace session." />
    {ownerQuery.isPending ? <Card className="p-6 text-sm text-muted">Loading profile…</Card> : owner ? <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <Card className="p-6">
        <SectionHeading title="Personal details" description="This account owns the documents, searches, and evaluation history in this workspace." />
        <div className="mt-6 flex items-center gap-4 rounded-2xl border border-border bg-background p-4"><span className="flex size-12 items-center justify-center rounded-2xl bg-citation text-primary"><UserRound size={22} /></span><div><p className="font-semibold">{owner.display_name}</p><p className="text-sm text-muted">Workspace member</p></div><Badge tone="success">Active</Badge></div>
        <dl className="mt-6 grid gap-4 sm:grid-cols-2"><div className="rounded-xl border border-border p-4"><dt className="flex items-center gap-2 text-xs font-semibold text-muted"><Mail size={14} />Email</dt><dd className="mt-2 break-all text-sm font-medium">{owner.email}</dd></div><div className="rounded-xl border border-border p-4"><dt className="flex items-center gap-2 text-xs font-semibold text-muted"><CalendarDays size={14} />Member since</dt><dd className="mt-2 text-sm font-medium">{new Date(owner.created_at).toLocaleDateString()}</dd></div></dl>
      </Card>
      <Card className="h-fit p-6"><span className="flex size-10 items-center justify-center rounded-xl bg-citation text-primary"><ShieldCheck size={18} /></span><h2 className="mt-5 text-lg font-semibold">Session & security</h2><p className="mt-2 text-sm leading-6 text-muted">Your session is stored in a secure browser cookie. Sign out when using a shared device.</p><Button className="mt-6 w-full" variant="danger" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}><LogOut size={15} />{logoutMutation.isPending ? 'Signing out…' : 'Sign out'}</Button></Card>
    </div> : <Card className="p-6 text-sm text-error">Profile could not be loaded.</Card>}
  </div>;
}

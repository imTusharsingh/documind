import { useQuery } from '@tanstack/react-query';
import { BarChart3, Clock3, Coins, Database, LoaderCircle, type LucideIcon } from 'lucide-react';

import { Badge, Card, PageHeader, SectionHeading } from '@/components/ui';
import { ApiError, fetchUsage } from '@/lib/api';

const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
const numberFormatter = new Intl.NumberFormat();
const statCards: { icon: LucideIcon; label: string; hint: string }[] = [
  { icon: Coins, label: 'Total tokens', hint: 'Input + output' },
  { icon: BarChart3, label: 'Requests', hint: 'Assistant responses' },
  { icon: Database, label: 'Input tokens', hint: 'Prompt processing' },
  { icon: Clock3, label: 'Output tokens', hint: 'Generated responses' },
];

export function UsagePage() {
  const usageQuery = useQuery({ queryKey: ['usage'], queryFn: ({ signal }) => fetchUsage(signal) });
  const usage = usageQuery.data;

  return <div className="space-y-8">
    <PageHeader eyebrow="Workspace analytics" title="Token usage" description="Track model activity across grounded answers. Usage is scoped to this workspace and refreshed from your API history." />
    {usageQuery.isError ? <div className="rounded-xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{usageQuery.error instanceof ApiError ? usageQuery.error.message : 'Usage history is unavailable.'}</div> : null}
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {statCards.map(({ icon: Icon, label, hint }, index) => { const value = [usage?.total_tokens, usage?.request_count, usage?.input_tokens, usage?.output_tokens][index] ?? 0; return <Card key={label} className="p-5"><div className="flex items-center justify-between"><span className="flex size-9 items-center justify-center rounded-lg bg-citation text-primary"><Icon aria-hidden="true" size={17} /></span><Badge tone="success">Live</Badge></div><p className="mt-5 text-xs font-semibold text-muted">{label}</p><p className="mt-1 text-2xl font-semibold tracking-tight">{numberFormatter.format(value)}</p><p className="mt-1 text-xs text-muted">{hint}</p></Card>; })}
    </section>
    <Card className="overflow-hidden"><div className="border-b border-border p-5"><SectionHeading title="Recent activity" description="The latest grounded answer requests and their token footprint." /></div>{usageQuery.isPending ? <div className="flex items-center gap-2 p-6 text-sm text-muted"><LoaderCircle className="animate-spin" size={15} />Loading usage…</div> : usage?.events.length ? <div className="divide-y divide-border">{usage.events.map((event) => <div key={event.id} className="grid gap-3 px-5 py-4 md:grid-cols-[minmax(0,1fr)_120px_120px_150px] md:items-center"><div className="min-w-0"><p className="truncate text-sm font-medium">{event.conversation_title}</p><p className="mt-1 text-xs text-muted">{dateFormatter.format(new Date(event.created_at))}</p></div><div><p className="text-xs text-muted">Total</p><p className="mt-1 font-mono text-sm">{numberFormatter.format(event.total_tokens)}</p></div><div><p className="text-xs text-muted">Latency</p><p className="mt-1 font-mono text-sm">{event.latency_ms ? `${event.latency_ms} ms` : '—'}</p></div><Badge tone="primary">Grounded answer</Badge></div>)}</div> : <div className="p-10 text-center"><p className="text-sm font-medium">No usage yet</p><p className="mt-1 text-sm text-muted">Ask a question to start building your usage history.</p></div>}</Card>
  </div>;
}

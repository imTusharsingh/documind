import { useQuery } from '@tanstack/react-query';
import { ArrowRight, BookOpen, CheckCircle2, FileText, MessageSquareText, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge, Card, PageHeader, SectionHeading } from '@/components/ui';
import { fetchDocuments, fetchHealth, fetchOwner } from '@/lib/api';

const actions = [
  { to: '/documents', title: 'Add documents', description: 'Upload PDFs and make them searchable.', icon: FileText },
  { to: '/search', title: 'Search knowledge', description: 'Find relevant passages with semantic search.', icon: Search },
  { to: '/chat', title: 'Ask a question', description: 'Get grounded answers with citations.', icon: MessageSquareText },
];

export function OverviewPage() {
  const healthQuery = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => fetchHealth(signal), refetchInterval: 30000 });
  const ownerQuery = useQuery({ queryKey: ['owner'], queryFn: ({ signal }) => fetchOwner(signal) });
  const documentsQuery = useQuery({ queryKey: ['documents'], queryFn: ({ signal }) => fetchDocuments(signal) });
  const documents = documentsQuery.data ?? [];
  const ready = documents.filter((document) => document.status === 'ready').length;
  const processing = documents.filter((document) => document.status === 'processing' || document.status === 'pending').length;

  return <div className="space-y-8">
    <PageHeader eyebrow="Research workspace" title={`Good to see you${ownerQuery.data?.display_name ? `, ${ownerQuery.data.display_name.split(' ')[0]}` : ''}.`} description="A focused home for your documents, answers, and retrieval quality. Everything you need to move from source material to insight." action={<Link to="/documents" className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-hover">Upload a document <ArrowRight size={15} /></Link>} />
    <section className="grid gap-4 md:grid-cols-3"><Card className="bg-primary p-6 text-white md:col-span-2"><div className="flex size-10 items-center justify-center rounded-xl bg-white/15"><Sparkles size={19} /></div><h2 className="mt-6 text-xl font-semibold tracking-tight">Your knowledge base is ready to work.</h2><p className="mt-2 max-w-lg text-sm leading-6 text-indigo-100">Upload research PDFs, search across them, and ask questions with page-level citations you can trust.</p><Link to="/chat" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white hover:text-indigo-100">Start asking <ArrowRight size={15} /></Link></Card><Card className="p-6"><div className="flex items-center justify-between"><span className="flex size-10 items-center justify-center rounded-xl bg-success/10 text-success"><ShieldCheck size={19} /></span><Badge tone={healthQuery.data?.status === 'ok' ? 'success' : 'warning'}>{healthQuery.data?.status === 'ok' ? 'Operational' : 'Checking'}</Badge></div><h2 className="mt-5 text-base font-semibold">Workspace health</h2><p className="mt-1 text-sm leading-5 text-muted">API and database connectivity.</p><div className="mt-5 flex items-center gap-2 text-xs font-medium text-success"><CheckCircle2 size={14} />{healthQuery.data?.dependencies.database?.status === 'up' ? 'All systems connected' : 'Checking services'}</div></Card></section>
    <section className="grid gap-4 sm:grid-cols-3"><Card className="p-5"><p className="text-xs font-semibold text-muted">Documents</p><p className="mt-2 text-2xl font-semibold">{documents.length}</p><p className="mt-1 text-xs text-muted">{ready} ready to search</p></Card><Card className="p-5"><p className="text-xs font-semibold text-muted">Ingestion</p><p className="mt-2 text-2xl font-semibold">{processing}</p><p className="mt-1 text-xs text-muted">{processing ? 'Processing now' : 'Nothing in progress'}</p></Card><Card className="p-5"><p className="text-xs font-semibold text-muted">Citations</p><p className="mt-2 text-2xl font-semibold">Page-level</p><p className="mt-1 text-xs text-muted">Every answer stays grounded</p></Card></section>
    <section><SectionHeading title="Jump back in" description="The fastest path to your next insight." /><div className="mt-4 grid gap-4 md:grid-cols-3">{actions.map(({ to, title, description, icon: Icon }) => <Link key={to} to={to} className="group"><Card className="h-full p-5 transition-all group-hover:-translate-y-0.5 group-hover:border-primary/40"><span className="flex size-9 items-center justify-center rounded-lg bg-citation text-primary"><Icon size={17} /></span><h3 className="mt-5 text-sm font-semibold">{title}</h3><p className="mt-1 text-sm leading-5 text-muted">{description}</p><span className="mt-5 inline-flex items-center gap-1 text-xs font-semibold text-primary">Open workspace <ArrowRight size={13} /></span></Card></Link>)}</div></section>
    <Card className="flex flex-wrap items-center justify-between gap-4 p-5"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-citation text-primary"><BookOpen size={17} /></span><div><p className="text-sm font-semibold">A reliable research loop</p><p className="mt-1 text-xs text-muted">Ingest → retrieve → answer → evaluate.</p></div></div><Link to="/evaluation" className="inline-flex items-center gap-1 text-xs font-semibold text-primary">Review evaluation <ArrowRight size={13} /></Link></Card>
  </div>;
}

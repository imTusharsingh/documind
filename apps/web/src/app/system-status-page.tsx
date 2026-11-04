import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Database,
  FileText,
  RefreshCw,
  Server,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { StatusIndicator, type Status } from '@/components/status-indicator';
import { fetchHealth, fetchOwner } from '@/lib/api';

const milestones = [
  {
    title: 'Document ingestion',
    description: 'PDF upload, page-aware extraction, chunking, and ingestion status.',
    icon: FileText,
    state: 'Available',
    to: '/documents',
  },
  {
    title: 'Embeddings and retrieval',
    description: 'pgvector storage and semantic search over document chunks.',
    icon: Database,
    state: 'Available',
    to: '/search',
  },
  {
    title: 'Grounded answers',
    description: 'RAG responses with validated page citations and source previews.',
    icon: Sparkles,
    state: 'Available',
    to: '/chat',
  },
  {
    title: 'Retrieval evaluation',
    description: 'Recall@k, MRR, and page-match metrics for question sets.',
    icon: Database,
    state: 'Available',
    to: '/evaluation',
  },
];

export function SystemStatusPage() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
  });

  const ownerQuery = useQuery({
    queryKey: ['owner'],
    queryFn: ({ signal }) => fetchOwner(signal),
  });

  const database = healthQuery.data?.dependencies.database;

  const apiStatus: Status = healthQuery.isPending
    ? 'checking'
    : healthQuery.isError
      ? 'offline'
      : healthQuery.data.status === 'ok'
        ? 'online'
        : 'degraded';

  const apiLabel = healthQuery.isPending
    ? 'Checking API'
    : healthQuery.isError
      ? 'API unreachable'
      : healthQuery.data.status === 'ok'
        ? 'API online'
        : 'API degraded';

  const databaseStatus: Status = healthQuery.isPending
    ? 'checking'
    : healthQuery.isError
      ? 'offline'
      : database?.status === 'up'
        ? 'online'
        : 'degraded';

  const databaseLabel = healthQuery.isPending
    ? 'Checking database'
    : healthQuery.isError
      ? 'Not checked'
      : database?.status === 'up'
        ? 'Database connected'
        : 'Database unavailable';

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
            Milestone 4
          </div>
          <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">System readiness</h1>
          <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
            DocuMind is running locally. This screen verifies the web application, the API, and its
            PostgreSQL connection alongside the document ingestion pipeline.
          </p>
        </div>

        <Link
          to="/documents"
          className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
        >
          Manage documents
          <ArrowRight aria-hidden="true" size={13} />
        </Link>
      </header>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <article className="rounded-lg border border-border bg-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-background text-primary">
              <Server aria-hidden="true" size={18} strokeWidth={2} />
            </div>
            <button
              type="button"
              onClick={() => void healthQuery.refetch()}
              disabled={healthQuery.isFetching}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface px-3 text-xs font-medium text-foreground transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                aria-hidden="true"
                size={13}
                className={healthQuery.isFetching ? 'animate-spin' : undefined}
              />
              Refresh
            </button>
          </div>

          <h2 className="mt-5 text-lg font-semibold leading-7">API service</h2>
          <p className="mt-1 text-sm leading-[22px] text-muted">
            FastAPI exposes the versioned API under <code className="font-mono">/api/v1</code>.
          </p>

          <div className="mt-5">
            <StatusIndicator status={apiStatus} label={apiLabel} />
          </div>

          {healthQuery.data ? (
            <dl className="mt-5 grid gap-3 border-t border-border pt-5 sm:grid-cols-3">
              <div>
                <dt className="text-xs font-medium text-muted">Service</dt>
                <dd className="mt-1 truncate text-sm font-medium">{healthQuery.data.service}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted">Version</dt>
                <dd className="mt-1 font-mono text-sm">{healthQuery.data.version}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted">Environment</dt>
                <dd className="mt-1 text-sm capitalize">{healthQuery.data.environment}</dd>
              </div>
            </dl>
          ) : null}

          <div className="mt-5 space-y-3 border-t border-border pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <StatusIndicator status={databaseStatus} label={databaseLabel} />
              {database?.latency_ms != null ? (
                <span className="font-mono text-[11px] text-muted">{database.latency_ms} ms</span>
              ) : null}
            </div>
            {database?.error ? (
              <p className="rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
                {database.error}
              </p>
            ) : null}
          </div>

          {healthQuery.isError ? (
            <p className="mt-5 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
              {healthQuery.error instanceof Error
                ? healthQuery.error.message
                : 'The API health check failed.'}
            </p>
          ) : null}

          <div className="mt-5 flex flex-wrap items-center gap-4 border-t border-border pt-5">
            <code className="rounded bg-background px-2 py-1 font-mono text-xs text-muted">
              GET /api/v1/health
            </code>
            <a
              href="/api/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary-hover"
            >
              Open API docs
              <ArrowUpRight aria-hidden="true" size={13} />
            </a>
          </div>
        </article>

        <article className="rounded-lg border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold leading-7">Environment</h2>
          <p className="mt-1 text-sm leading-[22px] text-muted">
            Services defined in Docker Compose for local development.
          </p>

          <ul className="mt-5 space-y-4">
            <li className="flex items-start gap-3">
              <span className="mt-0.5 flex size-5 items-center justify-center rounded-full bg-success/10 text-success">
                <Check aria-hidden="true" size={12} strokeWidth={2.5} />
              </span>
              <div>
                <p className="text-sm font-medium">Web application</p>
                <p className="mt-0.5 text-xs leading-5 text-muted">
                  Rsbuild dev server with React and Tailwind CSS
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-0.5 flex size-5 items-center justify-center rounded-full bg-success/10 text-success">
                <Check aria-hidden="true" size={12} strokeWidth={2.5} />
              </span>
              <div>
                <p className="text-sm font-medium">API container</p>
                <p className="mt-0.5 text-xs leading-5 text-muted">
                  FastAPI, Pydantic v2, and Uvicorn
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-0.5 flex size-5 items-center justify-center rounded-full bg-success/10 text-success">
                <Check aria-hidden="true" size={12} strokeWidth={2.5} />
              </span>
              <div>
                <p className="text-sm font-medium">Ingestion worker</p>
                <p className="mt-0.5 text-xs leading-5 text-muted">
                  Separate process that claims pending documents from PostgreSQL
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-0.5 flex size-5 items-center justify-center rounded-full bg-success/10 text-success">
                <Check aria-hidden="true" size={12} strokeWidth={2.5} />
              </span>
              <div>
                <p className="text-sm font-medium">PostgreSQL + pgvector</p>
                <p className="mt-0.5 text-xs leading-5 text-muted">
                  Schema managed by Alembic, applied when the API starts
                </p>
              </div>
            </li>
          </ul>

          <div className="mt-5 space-y-2 border-t border-border pt-4">
            <p className="flex items-center justify-between gap-3 text-xs leading-5 text-muted">
              <span>Liveness</span>
              <code className="font-mono">/health/live</code>
            </p>
            <p className="flex items-center justify-between gap-3 text-xs leading-5 text-muted">
              <span>Readiness</span>
              <code className="font-mono">/health</code>
            </p>
          </div>
        </article>
      </section>

      <section className="rounded-lg border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-background text-primary">
              <UserRound aria-hidden="true" size={18} strokeWidth={2} />
            </div>
            <div>
              <h2 className="text-lg font-semibold leading-7">Workspace owner</h2>
              <p className="mt-1 max-w-xl text-sm leading-[22px] text-muted">
                Read from PostgreSQL. The seeded development owner is the single identity used by
                the MVP until authentication is added.
              </p>
            </div>
          </div>
          <StatusIndicator
            status={ownerQuery.isError ? 'offline' : ownerQuery.isPending ? 'checking' : 'online'}
            label={
              ownerQuery.isError ? 'Owner unavailable' : ownerQuery.isPending ? 'Loading' : 'Managed'
            }
          />
        </div>

        {ownerQuery.data ? (
          <dl className="mt-5 grid gap-4 border-t border-border pt-5 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-medium text-muted">Name</dt>
              <dd className="mt-1 text-sm font-medium">{ownerQuery.data.display_name}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted">Email</dt>
              <dd className="mt-1 truncate text-sm">{ownerQuery.data.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted">Seeded</dt>
              <dd className="mt-1 font-mono text-xs text-muted">
                {ownerQuery.data.created_at.slice(0, 10)} · {ownerQuery.data.id.slice(0, 8)}
              </dd>
            </div>
          </dl>
        ) : null}

        {ownerQuery.isError ? (
          <p className="mt-5 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
            {ownerQuery.error instanceof Error
              ? ownerQuery.error.message
              : 'The owner record could not be loaded.'}
          </p>
        ) : null}
      </section>

      <section className="rounded-lg border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold leading-7">Build progress</h2>
        <p className="mt-1 text-sm leading-[22px] text-muted">
          Document ingestion and semantic retrieval are available now. Grounded answers build on
          the stored passages and citations.
        </p>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {milestones.map((milestone, index) => {
            const Icon = milestone.icon;
            const content = (
              <>
                <div className="flex items-center justify-between">
                  <Icon aria-hidden="true" size={16} className="text-muted" />
                  <span className="font-mono text-[11px] text-muted">
                    {String(index + 2).padStart(2, '0')}
                  </span>
                </div>
                <p className="mt-4 text-sm font-medium">{milestone.title}</p>
                <p className="mt-1 text-xs leading-5 text-muted">{milestone.description}</p>
                <p className="mt-3 text-[11px] font-medium uppercase tracking-wide text-muted">
                  {milestone.state}
                </p>
              </>
            );

            return milestone.to ? (
              <Link
                key={milestone.title}
                to={milestone.to}
                className="rounded-md border border-primary/30 bg-citation p-4 transition-colors hover:border-primary/50"
              >
                {content}
              </Link>
            ) : (
              <div key={milestone.title} className="rounded-md border border-border bg-background p-4">
                {content}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

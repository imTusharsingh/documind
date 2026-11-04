import { useMutation } from '@tanstack/react-query';
import { AlertCircle, FileSearch, LoaderCircle, Search } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { ApiError, searchDocuments, type SearchResult } from '@/lib/api';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return 'Search is unavailable right now.';
}

function similarityLabel(value: number): string {
  return `${Math.round(value * 100)}% match`;
}

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <article className="rounded-lg border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{result.document_name}</p>
          <p className="mt-1 text-xs text-muted">
            Page {result.page_number} · Chunk {result.chunk_index + 1}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-citation px-2.5 py-1 text-[11px] font-medium text-primary">
          {similarityLabel(result.similarity)}
        </span>
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-foreground">{result.content}</p>
    </article>
  );
}

export function SearchPage() {
  const [query, setQuery] = useState('');
  const searchMutation = useMutation({ mutationFn: searchDocuments });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (normalized && !searchMutation.isPending) {
      searchMutation.mutate(normalized);
    }
  }

  const results = searchMutation.data?.results ?? [];

  return (
    <div className="space-y-6">
      <header>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
          <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
          Milestone 3
        </div>
        <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">Search your documents</h1>
        <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
          Ask a question or describe a topic. Search ranks the closest embedded passages and keeps each result tied to its document page.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-surface p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="document-search">Search documents</label>
          <input
            id="document-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What do your documents say about…?"
            maxLength={2000}
            className="h-11 min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted focus:border-primary"
          />
          <button
            type="submit"
            disabled={!query.trim() || searchMutation.isPending}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {searchMutation.isPending ? <LoaderCircle aria-hidden="true" size={15} className="animate-spin" /> : <Search aria-hidden="true" size={15} />}
            Search
          </button>
        </form>
        {searchMutation.isError ? (
          <p className="mt-3 flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
            <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
            {errorMessage(searchMutation.error)}
          </p>
        ) : null}
      </section>

      {searchMutation.isSuccess ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold leading-7">Results</h2>
              <p className="text-xs text-muted">{results.length} passage{results.length === 1 ? '' : 's'} found</p>
            </div>
          </div>
          {results.length > 0 ? results.map((result) => <ResultCard key={`${result.document_id}-${result.chunk_index}`} result={result} />) : (
            <div className="flex flex-col items-center rounded-lg border border-dashed border-border px-6 py-12 text-center">
              <FileSearch aria-hidden="true" size={22} className="text-muted" />
              <p className="mt-3 text-sm font-medium">No matching passages</p>
              <p className="mt-1 text-xs text-muted">Try a broader query or upload another document.</p>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertCircle, BarChart3, Check, LoaderCircle, Play } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { ApiError, fetchDocuments, runEvaluation } from '@/lib/api';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return 'The evaluation could not be run.';
}

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function EvaluationPage() {
  const documentsQuery = useQuery({ queryKey: ['documents'], queryFn: () => fetchDocuments() });
  const [question, setQuestion] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [pageNumber, setPageNumber] = useState('1');
  const evaluationMutation = useMutation({
    mutationFn: () => runEvaluation(question.trim(), documentId, Number(pageNumber)),
  });
  const readyDocuments = (documentsQuery.data ?? []).filter((document) => document.status === 'ready');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (question.trim() && documentId && Number(pageNumber) > 0) evaluationMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <header>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
          <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
          Milestone 5
        </div>
        <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">Evaluate retrieval</h1>
        <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
          Run a small question set against your ready documents and measure whether retrieval finds the expected source page.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-surface p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="evaluation-question" className="text-xs font-medium text-muted">Question</label>
            <input
              id="evaluation-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What should retrieval find?"
              className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_120px]">
            <div>
              <label htmlFor="evaluation-document" className="text-xs font-medium text-muted">Expected document</label>
              <select
                id="evaluation-document"
                value={documentId}
                onChange={(event) => setDocumentId(event.target.value)}
                className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
              >
                <option value="">Choose a ready document</option>
                {readyDocuments.map((document) => <option key={document.id} value={document.id}>{document.original_filename}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="evaluation-page" className="text-xs font-medium text-muted">Expected page</label>
              <input
                id="evaluation-page"
                type="number"
                min="1"
                value={pageNumber}
                onChange={(event) => setPageNumber(event.target.value)}
                className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={!question.trim() || !documentId || evaluationMutation.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {evaluationMutation.isPending ? <LoaderCircle aria-hidden="true" size={15} className="animate-spin" /> : <Play aria-hidden="true" size={15} />}
            Run evaluation
          </button>
        </form>
        {evaluationMutation.isError ? <p className="mt-4 flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error"><AlertCircle aria-hidden="true" size={14} />{errorMessage(evaluationMutation.error)}</p> : null}
      </section>

      {evaluationMutation.data ? (
        <section className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            {[['Recall@k', evaluationMutation.data.recall_at_k], ['MRR', evaluationMutation.data.mean_reciprocal_rank], ['Page match', evaluationMutation.data.page_match_rate]].map(([label, value]) => (
              <div key={label as string} className="rounded-lg border border-border bg-surface p-4">
                <p className="text-xs font-medium text-muted">{label}</p>
                <p className="mt-2 text-2xl font-semibold">{percentage(value as number)}</p>
              </div>
            ))}
          </div>
          {evaluationMutation.data.results.map((result) => (
            <article key={result.question} className="rounded-lg border border-border bg-surface p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium">{result.question}</p>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-success"><Check aria-hidden="true" size={13} />{result.page_match ? 'Page found' : 'Page missed'}</span>
              </div>
              <p className="mt-3 text-xs text-muted">Recall@k {percentage(result.recall_at_k)} · Reciprocal rank {result.reciprocal_rank.toFixed(2)}</p>
              <div className="mt-3 flex items-center gap-2 text-xs text-muted"><BarChart3 aria-hidden="true" size={13} />{result.retrieved_sources.length} sources retrieved</div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}

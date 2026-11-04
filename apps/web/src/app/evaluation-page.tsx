import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertCircle, BarChart3, Check, LoaderCircle, Play } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { ApiError, createEvaluationDataset, fetchDocuments, fetchEvaluationDatasets, runEvaluation, runEvaluationDataset } from '@/lib/api';

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
  const [datasetName, setDatasetName] = useState('My retrieval set');
  const datasetsQuery = useQuery({ queryKey: ['evaluation-datasets'], queryFn: () => fetchEvaluationDatasets() });
  const evaluationMutation = useMutation({
    mutationFn: () => runEvaluation(question.trim(), documentId, Number(pageNumber)),
  });
  const createDatasetMutation = useMutation({
    mutationFn: () => createEvaluationDataset(datasetName.trim(), question.trim(), documentId, Number(pageNumber)),
    onSuccess: () => datasetsQuery.refetch(),
  });
  const runDatasetMutation = useMutation({ mutationFn: (id: string) => runEvaluationDataset(id) });
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
          Milestone 6
        </div>
        <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">Evaluate retrieval</h1>
        <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
          Save reusable question sets, rerun them after retrieval changes, and compare quality over time.
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
          <div className="border-t border-border pt-4">
            <label htmlFor="evaluation-dataset-name" className="text-xs font-medium text-muted">Save as dataset</label>
            <div className="mt-1 flex gap-2">
              <input id="evaluation-dataset-name" value={datasetName} onChange={(event) => setDatasetName(event.target.value)} className="h-10 min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary" />
              <button type="button" onClick={() => createDatasetMutation.mutate()} disabled={!datasetName.trim() || !question.trim() || !documentId || createDatasetMutation.isPending} className="h-10 rounded-md border border-border px-3 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50">Save dataset</button>
            </div>
          </div>
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

      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">Saved datasets</h2>
          <p className="mt-1 text-sm text-muted">Historical runs stay attached to the dataset that produced them.</p>
        </div>
        {datasetsQuery.isLoading ? <p className="text-sm text-muted">Loading datasets…</p> : null}
        {(datasetsQuery.data ?? []).map((dataset) => (
          <article key={dataset.id} className="rounded-lg border border-border bg-surface p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h3 className="text-sm font-medium">{dataset.name}</h3><p className="mt-1 text-xs text-muted">{dataset.case_count} case{dataset.case_count === 1 ? '' : 's'} · {dataset.run_count} historical run{dataset.run_count === 1 ? '' : 's'}</p></div>
              <button type="button" onClick={() => runDatasetMutation.mutate(dataset.id)} disabled={runDatasetMutation.isPending} className="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-white disabled:opacity-50"><Play aria-hidden="true" size={13} />Run again</button>
            </div>
            {dataset.latest_run ? <p className="mt-4 text-xs text-muted">Latest: Recall@k {percentage(dataset.latest_run.recall_at_k)} · MRR {dataset.latest_run.mean_reciprocal_rank.toFixed(2)} · Page match {percentage(dataset.latest_run.page_match_rate)}</p> : <p className="mt-4 text-xs text-muted">No runs yet.</p>}
          </article>
        ))}
      </section>
    </div>
  );
}

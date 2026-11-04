import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  FileText,
  LoaderCircle,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react';
import { useRef, useState, type ChangeEvent, type FormEvent } from 'react';

import { DocumentStatusBadge } from '@/components/document-status-badge';
import {
  ApiError,
  deleteDocument,
  fetchDocuments,
  uploadDocument,
  type DocumentResponse,
} from '@/lib/api';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

function isProcessing(document: DocumentResponse): boolean {
  return document.status === 'pending' || document.status === 'processing';
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: ({ signal }) => fetchDocuments(signal),
    refetchInterval: (query) =>
      query.state.data?.some(isProcessing) ? 2_000 : false,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      setSelectedFile(null);
      setLocalError(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      void queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      setConfirmingId(null);
      void queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const documents = documentsQuery.data ?? [];
  const busyCount = documents.filter(isProcessing).length;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    uploadMutation.reset();
    setLocalError(null);

    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(null);
      event.target.value = '';
      setLocalError('Only PDF files are supported.');
      return;
    }

    setSelectedFile(file);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || uploadMutation.isPending) {
      return;
    }
    uploadMutation.mutate(selectedFile);
  }

  function handleConfirmDelete(documentId: string) {
    deleteMutation.reset();
    setConfirmingId(documentId);
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
            Milestone 3
          </div>
          <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">Documents</h1>
          <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
            Upload PDFs to the research workspace. A background worker extracts text, splits it
            into page-aware chunks, embeds them, and makes them available for semantic search.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void documentsQuery.refetch()}
          disabled={documentsQuery.isFetching}
          className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-surface px-3 text-xs font-medium text-foreground transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            aria-hidden="true"
            size={13}
            className={documentsQuery.isFetching ? 'animate-spin' : undefined}
          />
          Refresh
        </button>
      </header>

      <section className="rounded-lg border border-border bg-surface p-6">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-background text-primary">
            <Upload aria-hidden="true" size={18} strokeWidth={2} />
          </div>
          <div>
            <h2 className="text-lg font-semibold leading-7">Upload a PDF</h2>
            <p className="mt-1 text-sm leading-[22px] text-muted">
              Files are stored by document id, checked for a PDF signature, and rejected if they
              exceed the server's upload limit. Scanned PDFs without a text layer are reported as
              failed.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-md border border-dashed border-border bg-background px-4 py-3 transition-colors hover:border-primary/40">
              <FileText aria-hidden="true" size={18} className="shrink-0 text-muted" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">
                  {selectedFile ? selectedFile.name : 'Choose a PDF file'}
                </span>
                <span className="block text-xs leading-5 text-muted">
                  {selectedFile
                    ? formatBytes(selectedFile.size)
                    : 'PDF only, up to 25 MB per file'}
                </span>
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                onChange={handleFileChange}
                className="sr-only"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploadMutation.isPending ? (
                <LoaderCircle aria-hidden="true" size={15} className="animate-spin" />
              ) : (
                <Upload aria-hidden="true" size={15} />
              )}
              {uploadMutation.isPending ? 'Uploading' : 'Upload document'}
            </button>
          </div>

          {localError ? (
            <p className="flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
              <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
              {localError}
            </p>
          ) : null}

          {uploadMutation.isError ? (
            <p className="flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
              <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
              {errorMessage(uploadMutation.error, 'The upload failed.')}
            </p>
          ) : null}
        </form>
      </section>

      <section className="rounded-lg border border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold leading-7">Library</h2>
            <p className="text-xs leading-5 text-muted">
              {documents.length === 0
                ? 'No documents yet.'
                : `${documents.length} document${documents.length === 1 ? '' : 's'}${
                    busyCount > 0 ? ` · ${busyCount} in progress` : ''
                  }`}
            </p>
          </div>
          {busyCount > 0 ? (
            <span className="inline-flex items-center gap-2 text-xs font-medium text-muted">
              <LoaderCircle aria-hidden="true" size={13} className="animate-spin" />
              Refreshing while ingestion runs
            </span>
          ) : null}
        </div>

        {documentsQuery.isError ? (
          <div className="border-b border-border px-6 py-4">
            <p className="flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
              <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
              {errorMessage(documentsQuery.error, 'The document list could not be loaded.')}
            </p>
          </div>
        ) : null}

        {deleteMutation.isError ? (
          <div className="border-b border-border px-6 py-4">
            <p className="flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
              <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
              {errorMessage(deleteMutation.error, 'The document could not be deleted.')}
            </p>
          </div>
        ) : null}

        {documentsQuery.isPending ? (
          <div className="flex items-center gap-2 px-6 py-10 text-sm text-muted">
            <LoaderCircle aria-hidden="true" size={15} className="animate-spin" />
            Loading documents…
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-background text-muted">
              <FileText aria-hidden="true" size={18} />
            </div>
            <p className="mt-3 text-sm font-medium">No documents uploaded</p>
            <p className="mt-1 max-w-sm text-xs leading-5 text-muted">
              Upload a text-based PDF above. It will appear here as queued, then processing, then
              ready once the worker has stored its chunks.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <caption className="sr-only">Uploaded documents and their ingestion status</caption>
              <thead>
                <tr className="border-b border-border text-xs font-medium text-muted">
                  <th scope="col" className="px-6 py-3 font-medium">
                    Document
                  </th>
                  <th scope="col" className="px-3 py-3 font-medium">
                    Status
                  </th>
                  <th scope="col" className="px-3 py-3 font-medium">
                    Pages
                  </th>
                  <th scope="col" className="px-3 py-3 font-medium">
                    Chunks
                  </th>
                  <th scope="col" className="px-3 py-3 font-medium">
                    Uploaded
                  </th>
                  <th scope="col" className="px-6 py-3 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id} className="border-b border-border last:border-b-0">
                    <td className="max-w-[320px] px-6 py-4 align-top">
                      <div className="flex items-start gap-2.5">
                        <FileText
                          aria-hidden="true"
                          size={16}
                          className="mt-0.5 shrink-0 text-muted"
                        />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">
                            {document.original_filename}
                          </p>
                          <p className="mt-0.5 font-mono text-[11px] text-muted">
                            {formatBytes(document.size_bytes)} · {document.id.slice(0, 8)}
                          </p>
                          {document.status === 'failed' && document.error_message ? (
                            <p className="mt-2 rounded border border-error/20 bg-error/5 px-2 py-1 text-[11px] leading-4 text-error">
                              {document.error_message}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-4 align-top">
                      <DocumentStatusBadge status={document.status} />
                    </td>
                    <td className="px-3 py-4 align-top font-mono text-xs text-muted">
                      {document.page_count ?? '—'}
                    </td>
                    <td className="px-3 py-4 align-top font-mono text-xs text-muted">
                      {document.chunk_count ?? '—'}
                    </td>
                    <td className="px-3 py-4 align-top text-xs text-muted">
                      {formatDate(document.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right align-top">
                      {confirmingId === document.id ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => deleteMutation.mutate(document.id)}
                            disabled={deleteMutation.isPending}
                            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-error px-2.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {deleteMutation.isPending ? (
                              <LoaderCircle aria-hidden="true" size={12} className="animate-spin" />
                            ) : null}
                            Confirm
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmingId(null)}
                            disabled={deleteMutation.isPending}
                            className="inline-flex h-8 items-center rounded-md border border-border bg-surface px-2.5 text-xs font-medium transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleConfirmDelete(document.id)}
                          aria-label={`Delete ${document.original_filename}`}
                          className="inline-flex size-8 items-center justify-center rounded-md border border-border bg-surface text-muted transition-colors hover:border-error/30 hover:bg-error/5 hover:text-error"
                        >
                          <Trash2 aria-hidden="true" size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

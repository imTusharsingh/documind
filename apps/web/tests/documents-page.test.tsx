import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, rstest, test } from '@rstest/core';
import { render, screen, waitFor } from '@testing-library/react';

import { DocumentsPage } from '@/app/documents-page';
import type { DocumentResponse } from '@/lib/api';

const originalFetch = globalThis.fetch;

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentsPage />
    </QueryClientProvider>,
  );
}

function mockDocuments(documents: DocumentResponse[]) {
  globalThis.fetch = rstest.fn(
    async () =>
      new Response(JSON.stringify(documents), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
  ) as unknown as typeof fetch;
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

const readyDocument: DocumentResponse = {
  id: '11111111-1111-4111-8111-111111111111',
  original_filename: 'research-paper.pdf',
  content_type: 'application/pdf',
  size_bytes: 4096,
  status: 'ready',
  page_count: 12,
  chunk_count: 28,
  error_message: null,
  created_at: '2026-11-04T10:00:00Z',
  updated_at: '2026-11-04T10:01:00Z',
};

const failedDocument: DocumentResponse = {
  id: '22222222-2222-4222-8222-222222222222',
  original_filename: 'scanned-report.pdf',
  content_type: 'application/pdf',
  size_bytes: 8192,
  status: 'failed',
  page_count: null,
  chunk_count: null,
  error_message: 'This PDF has no extractable text. Scanned PDFs are not supported.',
  created_at: '2026-11-04T09:00:00Z',
  updated_at: '2026-11-04T09:01:00Z',
};

test('renders documents with their status, counts, and failure reason', async () => {
  mockDocuments([readyDocument, failedDocument]);
  renderPage();

  await waitFor(() => {
    expect(screen.getByText('research-paper.pdf')).toBeInTheDocument();
  });

  expect(screen.getByText('Ready')).toBeInTheDocument();
  expect(screen.getByText('Failed')).toBeInTheDocument();
  expect(screen.getByText('12')).toBeInTheDocument();
  expect(screen.getByText('28')).toBeInTheDocument();
  expect(
    screen.getByText('This PDF has no extractable text. Scanned PDFs are not supported.'),
  ).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: 'Delete research-paper.pdf' }),
  ).toBeInTheDocument();
});

test('shows an empty state when the library has no documents', async () => {
  mockDocuments([]);
  renderPage();

  await waitFor(() => {
    expect(screen.getByText('No documents uploaded')).toBeInTheDocument();
  });

  expect(screen.getByText('No documents yet.')).toBeInTheDocument();
});

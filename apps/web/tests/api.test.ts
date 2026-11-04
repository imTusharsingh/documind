import { afterEach, expect, rstest, test } from '@rstest/core';

import {
  ApiError,
  deleteDocument,
  fetchDocuments,
  fetchHealth,
  fetchOwner,
  uploadDocument,
} from '@/lib/api';

const originalFetch = globalThis.fetch;

function mockFetch(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Response,
) {
  globalThis.fetch = rstest.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => handler(input, init),
  ) as unknown as typeof fetch;
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('returns a degraded health payload instead of throwing on 503', async () => {
  mockFetch(
    () =>
      new Response(
        JSON.stringify({
          status: 'degraded',
          service: 'DocuMind API',
          version: '0.1.0',
          environment: 'development',
          dependencies: {
            database: {
              status: 'down',
              latency_ms: null,
              error: 'Database connection failed.',
            },
          },
        }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      ),
  );

  const health = await fetchHealth();

  expect(health.status).toBe('degraded');
  expect(health.dependencies.database?.status).toBe('down');
});

test('surfaces the API error envelope on the owner request', async () => {
  mockFetch(
    () =>
      new Response(
        JSON.stringify({
          error: {
            code: 'DEVELOPMENT_OWNER_MISSING',
            message: 'The development owner is missing.',
            details: null,
          },
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } },
      ),
  );

  try {
    await fetchOwner();
    throw new Error('fetchOwner should have thrown.');
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('DEVELOPMENT_OWNER_MISSING');
    expect((error as ApiError).status).toBe(500);
  }
});

const documentPayload = {
  id: '2b1f2f52-5f10-4c43-a6a0-7a6f2f6c1f11',
  original_filename: 'report.pdf',
  content_type: 'application/pdf',
  size_bytes: 2048,
  status: 'pending',
  page_count: null,
  chunk_count: null,
  error_message: null,
  created_at: '2026-11-04T10:00:00Z',
  updated_at: '2026-11-04T10:00:00Z',
};

test('lists documents from the versioned endpoint', async () => {
  mockFetch(() =>
    new Response(JSON.stringify([documentPayload]), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );

  const documents = await fetchDocuments();

  expect(documents).toHaveLength(1);
  expect(documents[0]?.original_filename).toBe('report.pdf');
  expect(documents[0]?.status).toBe('pending');
});

test('uploads a file as multipart form data without setting a content type', async () => {
  let captured: RequestInit | undefined;
  mockFetch((_input, init) => {
    captured = init;
    return new Response(JSON.stringify(documentPayload), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  });

  const file = new File(['%PDF-1.7'], 'report.pdf', { type: 'application/pdf' });
  const uploaded = await uploadDocument(file);

  expect(uploaded.id).toBe(documentPayload.id);
  expect(captured?.method).toBe('POST');
  expect(captured?.body).toBeInstanceOf(FormData);
  expect((captured?.body as FormData).get('file')).toBe(file);
  // The browser must add the multipart boundary itself.
  expect((captured?.headers as Record<string, string> | undefined)?.['Content-Type']).toBeUndefined();
});

test('maps an oversized upload to the API error envelope', async () => {
  mockFetch(
    () =>
      new Response(
        JSON.stringify({
          error: {
            code: 'PAYLOAD_TOO_LARGE',
            message: 'The file exceeds the 25 MB upload limit.',
            details: null,
          },
        }),
        { status: 413, headers: { 'Content-Type': 'application/json' } },
      ),
  );

  try {
    await uploadDocument(new File(['x'], 'big.pdf', { type: 'application/pdf' }));
    throw new Error('uploadDocument should have thrown.');
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('PAYLOAD_TOO_LARGE');
    expect((error as ApiError).status).toBe(413);
  }
});

test('delete resolves on 204 and surfaces a missing document', async () => {
  mockFetch(() => new Response(null, { status: 204 }));

  await expect(deleteDocument(documentPayload.id)).resolves.toBeUndefined();

  globalThis.fetch = rstest.fn(
    async () =>
      new Response(
        JSON.stringify({
          error: { code: 'NOT_FOUND', message: 'Document was not found.', details: null },
        }),
        { status: 404, headers: { 'Content-Type': 'application/json' } },
      ),
  ) as unknown as typeof fetch;

  await expect(deleteDocument(documentPayload.id)).rejects.toMatchObject({
    code: 'NOT_FOUND',
    status: 404,
  });
});

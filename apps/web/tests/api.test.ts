import { afterEach, expect, rstest, test } from '@rstest/core';

import { ApiError, fetchHealth, fetchOwner } from '@/lib/api';

const originalFetch = globalThis.fetch;

function mockFetch(handler: () => Response) {
  globalThis.fetch = rstest.fn(async () => handler()) as unknown as typeof fetch;
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

export interface DependencyStatus {
  status: 'up' | 'down';
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  service: string;
  version: string;
  environment: string;
  dependencies: Record<string, DependencyStatus>;
}

export interface OwnerResponse {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface DocumentResponse {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  page_count: number | null;
  chunk_count: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, message: string, code = 'HTTP_ERROR') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as Partial<ErrorEnvelope>;
    if (body.error?.message) {
      return new ApiError(response.status, body.error.message, body.error.code);
    }
  } catch {
    // The body was not JSON; fall through to the generic message.
  }

  return new ApiError(response.status, `Request failed with status ${response.status}.`);
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  // 503 carries a valid readiness body: the API is up but degraded.
  // Surfacing that payload is more useful than throwing it away.
  if (response.status !== 200 && response.status !== 503) {
    throw await toApiError(response);
  }

  return (await response.json()) as HealthResponse;
}

export async function fetchOwner(signal?: AbortSignal): Promise<OwnerResponse> {
  const response = await fetch('/api/v1/me', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as OwnerResponse;
}

export async function fetchDocuments(signal?: AbortSignal): Promise<DocumentResponse[]> {
  const response = await fetch('/api/v1/documents', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as DocumentResponse[];
}

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const body = new FormData();
  body.append('file', file);

  const response = await fetch('/api/v1/documents', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
    body,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as DocumentResponse;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`/api/v1/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw await toApiError(response);
  }
}

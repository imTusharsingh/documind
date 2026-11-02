export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
  environment: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(response.status, `Health check failed with status ${response.status}.`);
  }

  return (await response.json()) as HealthResponse;
}

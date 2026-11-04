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

export interface SearchResult {
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_index: number;
  content: string;
  similarity: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_index: number;
  quote: string;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  insufficient_evidence: boolean;
}

export interface EvaluationSource {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_index: number;
  similarity: number;
}

export interface EvaluationCaseResult {
  question: string;
  recall_at_k: number;
  reciprocal_rank: number;
  page_match: boolean;
  retrieved_sources: EvaluationSource[];
}

export interface EvaluationResponse {
  case_count: number;
  recall_at_k: number;
  mean_reciprocal_rank: number;
  page_match_rate: number;
  results: EvaluationCaseResult[];
}

export interface EvaluationRunSummary {
  id: string;
  top_k: number;
  min_similarity: number;
  case_count: number;
  recall_at_k: number;
  mean_reciprocal_rank: number;
  page_match_rate: number;
  label: string | null;
  embedding_model: string | null;
  regression_passed: boolean | null;
  regression_failures: string[] | null;
  created_at: string;
}

export interface EvaluationDataset {
  id: string;
  name: string;
  description: string | null;
  case_count: number;
  run_count: number;
  latest_run: EvaluationRunSummary | null;
  created_at: string;
  updated_at: string;
  minimum_recall_at_k: number | null;
  minimum_mrr: number | null;
  minimum_page_match_rate: number | null;
}

export interface EvaluationDatasetDetail extends EvaluationDataset {
  cases: { question: string; expected_sources: { document_id: string; page_number: number }[] }[];
  runs: EvaluationRunSummary[];
}

export interface EvaluationDraftCase {
  question: string;
  documentId: string;
  pageNumber: number;
}

export interface PersistentEvaluationResponse extends EvaluationRunSummary {
  dataset_id: string;
  results: EvaluationCaseResult[];
}

export interface EvaluationTrendResponse {
  dataset_id: string;
  runs: EvaluationRunSummary[];
}

export interface EvaluationReportResponse {
  dataset: EvaluationDataset;
  runs: EvaluationRunSummary[];
  generated_at: string;
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

export async function searchDocuments(query: string, signal?: AbortSignal): Promise<SearchResponse> {
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, limit: 8 }),
    signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as SearchResponse;
}

export async function askQuestion(
  question: string,
  conversationId?: string,
): Promise<ChatResponse> {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as ChatResponse;
}

export async function runEvaluation(
  question: string,
  documentId: string,
  pageNumber: number,
): Promise<EvaluationResponse> {
  const response = await fetch('/api/v1/evaluation/run', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      cases: [{ question, expected_sources: [{ document_id: documentId, page_number: pageNumber }] }],
      top_k: 5,
    }),
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as EvaluationResponse;
}

export async function fetchEvaluationDatasets(signal?: AbortSignal): Promise<EvaluationDataset[]> {
  const response = await fetch('/api/v1/evaluation/datasets', { headers: { Accept: 'application/json' }, signal });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as EvaluationDataset[];
}

export async function createEvaluationDataset(
  name: string,
  cases: EvaluationDraftCase[],
  thresholds?: { recall?: number; mrr?: number; pageMatch?: number },
): Promise<EvaluationDatasetDetail> {
  const response = await fetch('/api/v1/evaluation/datasets', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      cases: cases.map((item) => ({ question: item.question, expected_sources: [{ document_id: item.documentId, page_number: item.pageNumber }] })),
      minimum_recall_at_k: thresholds?.recall ?? null,
      minimum_mrr: thresholds?.mrr ?? null,
      minimum_page_match_rate: thresholds?.pageMatch ?? null,
    }),
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as EvaluationDatasetDetail;
}

export async function runEvaluationDataset(
  datasetId: string,
  label?: string,
  embeddingModel?: string,
): Promise<PersistentEvaluationResponse> {
  const response = await fetch(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}/runs`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ top_k: 5, label: label?.trim() || null, embedding_model: embeddingModel?.trim() || null }),
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as PersistentEvaluationResponse;
}

export async function updateEvaluationDataset(
  datasetId: string,
  name: string,
  description: string,
): Promise<EvaluationDatasetDetail> {
  const response = await fetch(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}`, {
    method: 'PATCH',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as EvaluationDatasetDetail;
}

export async function fetchEvaluationTrend(datasetId: string): Promise<EvaluationTrendResponse> {
  const response = await fetch(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}/trend`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as EvaluationTrendResponse;
}

export async function fetchEvaluationReport(datasetId: string): Promise<EvaluationReportResponse> {
  const response = await fetch(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}/report`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as EvaluationReportResponse;
}

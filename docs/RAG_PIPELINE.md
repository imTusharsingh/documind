# RAG pipeline

This document describes the full retrieval-augmented generation pipeline. Milestone 3 implements upload, storage, extraction, chunking, embeddings, and semantic retrieval. Answer generation remains future work.

## Ingestion

Implemented in Milestone 2 and retained in Milestone 3:

1. Validate the uploaded file name, PDF signature, and size while streaming it to disk.
2. Store the original file on the persistent uploads volume under a server-generated document id.
3. Create a `documents` row with status `pending`.
4. The worker claims the row atomically and sets status `processing`.
5. Extract text page by page with PyMuPDF.
6. If no extractable text exists, fail with an explicit message explaining that scanned PDFs are not supported.
7. Split each page into overlapping token windows with `tiktoken` (`cl100k_base`, 350 tokens, 50 overlap).
8. Store chunks with page number, sequential chunk index, content, and token count.
9. Set the document status to `ready` with `page_count` and `chunk_count` in the same transaction.

Implemented in Milestone 3:

10. Generate embeddings in batches with the configured OpenAI provider.
11. Store 1536-dimensional vectors alongside each chunk and add an HNSW pgvector cosine index.
12. Extend readiness or failure handling so a document is only `ready` when its vectors exist.
13. Embed search queries and rank ready chunks with cosine similarity in PostgreSQL.
14. Filter retrieval by owner, optional document IDs, readiness, result count, and minimum similarity.

The `POST /documents/{id}/reprocess` endpoint requeues ready or failed documents. This makes provider configuration failures recoverable and supports deliberate re-embedding after a model migration.

Chunking within page boundaries keeps citations precise. Cross-page chunks may be evaluated later if retrieval quality requires them.

## Question answering

Implemented in Milestone 4:

1. Receive the question and optional document selection.
2. Resolve the conversation and owner.
3. Validate that selected documents are owned by the user and ready.
4. Embed the question with the same embedding model used during ingestion.
5. Perform cosine similarity search in pgvector.
6. Filter by owner, ready status, optional document IDs, and minimum similarity.
7. Build a prompt from the top-k passages.
8. Ask the model for a structured answer with chunk IDs and page numbers.
9. Validate every citation against the retrieved chunk set.
10. Remove invalid citations.
11. Return an explicit insufficient-evidence response when no valid evidence exists.
12. Persist the user message, assistant message, citations, token usage, and latency.
13. Expose conversation history with owner-scoped endpoints.

## Key properties

- No separate vector database.
- No hidden LangChain/LlamaIndex pipeline.
- Retrieval is inspectable SQL.
- Chunks remain attached to their document and page.
- Owner filtering happens in the database query.
- Citations are validated by application code, not trusted from the model.
- The answer must not use outside knowledge when the documents do not support it.
- Invalid model citations are removed before persistence and response serialization.
- Every persisted assistant citation points to the retrieved chunk used for that answer.
- Ingestion progress is durable because status lives in PostgreSQL, not in process memory.

## Evaluation

Milestone 5 implements a stateless evaluation endpoint. A request contains questions, expected source document/page pairs, `top_k`, and a minimum similarity. Initial metrics:

- Recall@k
- Mean reciprocal rank (MRR)
- Citation validity rate
- Citation page match rate when running answer generation
- Average latency and token usage

Results are returned to the frontend and can be inspected in the Evaluation page. Milestone 6 persists datasets, validates their expected sources against the owner, and stores immutable run summaries and per-case retrieved sources for historical comparison.

Persistent evaluation data is deliberately separate from production document chunks: a dataset records the test intent, while each run records the retrieval configuration and observed results. This makes a run reproducible enough to compare changes without mutating older evidence.

Milestone 7 adds explicit run labels and embedding-model metadata so a chart can compare retrieval configurations without treating two runs as equivalent. Dataset edits replace the case snapshot for future runs; existing run records remain immutable.

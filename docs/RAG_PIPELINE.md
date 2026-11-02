# RAG pipeline

This document describes the pipeline that will be implemented in Milestones 2–4. Nothing below is implemented yet beyond the empty infrastructure.

## Ingestion

1. Validate the uploaded PDF.
2. Store the original file on a persistent upload volume.
3. Create a document row with status `pending`.
4. The worker claims the row and sets status `processing`.
5. Extract text page by page with PyMuPDF.
6. If no extractable text exists, fail with an explicit message explaining that scanned PDFs are not supported.
7. Split each page into fixed-size token chunks with overlap.
8. Generate embeddings in batches.
9. Store chunks, page numbers, token counts, metadata, and vectors.
10. Set the document status to `ready`.

Chunking within page boundaries keeps citations precise. Cross-page chunks may be evaluated later if retrieval quality requires them.

## Question answering

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

## Key properties

- No separate vector database.
- No hidden LangChain/LlamaIndex pipeline.
- Retrieval is inspectable SQL.
- Chunks remain attached to their document and page.
- Owner filtering happens in the database query.
- Citations are validated by application code, not trusted from the model.
- The answer must not use outside knowledge when the documents do not support it.

## Evaluation

The evaluation dataset will contain questions, expected source documents/pages, and retrieval configuration. Initial metrics:

- Recall@k
- Mean reciprocal rank (MRR)
- Citation validity rate
- Citation page match rate when running answer generation
- Average latency and token usage

The evaluation endpoint will be stateless for the MVP. Results will be returned to the frontend and can be inspected in the Evaluation page.

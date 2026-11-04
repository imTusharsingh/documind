import { useMutation } from '@tanstack/react-query';
import { AlertCircle, BookOpen, LoaderCircle, Send, Sparkles } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { ApiError, askQuestion, type ChatResponse } from '@/lib/api';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return 'The grounded answer service is unavailable right now.';
}

function Answer({ response }: { response: ChatResponse }) {
  return (
    <article className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Sparkles aria-hidden="true" size={15} className="text-primary" />
        Answer
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-6">{response.answer}</p>
      {response.citations.length > 0 ? (
        <div className="mt-5 border-t border-border pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Sources</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {response.citations.map((citation) => (
              <div key={citation.chunk_id} className="rounded-md border border-border bg-citation p-3">
                <div className="flex items-center gap-2 text-xs font-medium text-primary">
                  <BookOpen aria-hidden="true" size={13} />
                  {citation.document_name} · page {citation.page_number}
                </div>
                <p className="mt-2 line-clamp-4 text-xs leading-5 text-muted">{citation.quote}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

export function ChatPage() {
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string>();
  const askMutation = useMutation({
    mutationFn: ({ text, id }: { text: string; id?: string }) => askQuestion(text, id),
    onSuccess: (response) => setConversationId(response.conversation_id),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = question.trim();
    if (normalized && !askMutation.isPending) {
      askMutation.mutate({ text: normalized, id: conversationId });
      setQuestion('');
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
          <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
          Milestone 4
        </div>
        <h1 className="text-2xl font-semibold leading-8 tracking-[-0.02em]">Ask your documents</h1>
        <p className="mt-1 max-w-2xl text-sm leading-[22px] text-muted">
          Answers are grounded in retrieved passages and include page-level sources. When the documents do not support an answer, DocuMind says so.
        </p>
      </header>

      <section className="space-y-4">
        {askMutation.data ? <Answer response={askMutation.data} /> : (
          <div className="rounded-lg border border-dashed border-border px-6 py-12 text-center">
            <Sparkles aria-hidden="true" size={24} className="mx-auto text-muted" />
            <p className="mt-3 text-sm font-medium">Ready to research</p>
            <p className="mt-1 text-xs text-muted">Ask a question about your uploaded documents.</p>
          </div>
        )}
        {askMutation.isError ? (
          <p className="flex items-start gap-2 rounded-md border border-error/20 bg-error/5 px-3 py-2 text-xs leading-5 text-error">
            <AlertCircle aria-hidden="true" size={14} className="mt-0.5 shrink-0" />
            {errorMessage(askMutation.error)}
          </p>
        ) : null}
      </section>

      <form onSubmit={handleSubmit} className="sticky bottom-4 rounded-lg border border-border bg-surface p-4 shadow-sm">
        <label className="sr-only" htmlFor="chat-question">Ask a question</label>
        <div className="flex gap-3">
          <textarea
            id="chat-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a grounded question…"
            rows={2}
            maxLength={4000}
            className="min-h-11 min-w-0 flex-1 resize-y rounded-md border border-border bg-background px-3 py-2 text-sm leading-5 outline-none placeholder:text-muted focus:border-primary"
          />
          <button
            type="submit"
            disabled={!question.trim() || askMutation.isPending}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 self-end rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {askMutation.isPending ? <LoaderCircle aria-hidden="true" size={15} className="animate-spin" /> : <Send aria-hidden="true" size={15} />}
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}

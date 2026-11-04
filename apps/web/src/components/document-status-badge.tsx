import type { DocumentStatus } from '@/lib/api';
import { cn } from '@/lib/utils';

export const documentStatusLabels: Record<DocumentStatus, string> = {
  pending: 'Queued',
  processing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
};

const statusStyles: Record<DocumentStatus, string> = {
  pending: 'border-warning/20 bg-warning/5 text-warning',
  processing: 'border-primary/20 bg-citation text-primary',
  ready: 'border-success/20 bg-success/5 text-success',
  failed: 'border-error/20 bg-error/5 text-error',
};

const dotStyles: Record<DocumentStatus, string> = {
  pending: 'bg-warning',
  processing: 'bg-primary animate-pulse',
  ready: 'bg-success',
  failed: 'bg-error',
};

interface DocumentStatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

export function DocumentStatusBadge({ status, className }: DocumentStatusBadgeProps) {
  return (
    <span
      role="status"
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium',
        statusStyles[status],
        className,
      )}
    >
      <span aria-hidden="true" className={cn('size-1.5 rounded-full', dotStyles[status])} />
      {documentStatusLabels[status]}
    </span>
  );
}

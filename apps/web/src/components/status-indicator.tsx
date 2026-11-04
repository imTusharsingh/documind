import { cn } from '@/lib/utils';

export type Status = 'checking' | 'degraded' | 'offline' | 'online';

const dotStyles: Record<Status, string> = {
  checking: 'bg-warning',
  degraded: 'bg-warning',
  offline: 'bg-error',
  online: 'bg-success',
};

interface StatusIndicatorProps {
  status: Status;
  label: string;
  className?: string;
}

export function StatusIndicator({ status, label, className }: StatusIndicatorProps) {
  return (
    <span
      role="status"
      className={cn('inline-flex items-center gap-2 text-xs font-medium text-muted', className)}
    >
      <span
        aria-hidden="true"
        className={cn(
          'size-1.5 rounded-full',
          dotStyles[status],
          status === 'checking' && 'animate-pulse',
        )}
      />
      {label}
    </span>
  );
}

import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function Button({ className, variant = 'primary', size = 'md', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md' }) {
  return <button {...props} className={cn('inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:pointer-events-none disabled:opacity-50', size === 'sm' ? 'h-8 px-3 text-xs' : 'h-10 px-4 text-sm', { primary: 'bg-primary text-white shadow-sm hover:bg-primary-hover', secondary: 'border border-border bg-surface text-foreground hover:bg-background', ghost: 'text-muted hover:bg-background hover:text-foreground', danger: 'border border-error/20 bg-error/5 text-error hover:bg-error/10' }[variant], className)} />;
}

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={cn('rounded-2xl border border-border bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.03)]', className)}>{children}</div>;
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'error' | 'primary' }) {
  return <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold', { neutral: 'bg-background text-muted', success: 'bg-success/10 text-success', warning: 'bg-warning/10 text-warning', error: 'bg-error/10 text-error', primary: 'bg-citation text-primary' }[tone])}><span className="size-1.5 rounded-full bg-current" aria-hidden="true" />{children}</span>;
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="flex flex-wrap items-end justify-between gap-5"><div><div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow ? <><span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />{eyebrow}</> : null}</div><h1 className="text-3xl font-semibold tracking-[-0.035em] text-foreground">{title}</h1>{description ? <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p> : null}</div>{action}</header>;
}

export function Field({ label, hint, className, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return <label className={cn('block', className)}><span className="text-xs font-semibold text-foreground">{label}</span><input {...props} className="mt-2 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground shadow-sm outline-none transition-colors placeholder:text-muted/70 focus:border-primary focus:ring-2 focus:ring-primary/10" />{hint ? <span className="mt-1.5 block text-xs leading-5 text-muted">{hint}</span> : null}</label>;
}

export function SectionHeading({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-semibold tracking-tight">{title}</h2>{description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}</div>{action}</div>;
}

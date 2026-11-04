import { LayoutDashboard, LibraryBig } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px]">
        <aside className="hidden w-60 shrink-0 border-r border-border bg-surface md:flex md:flex-col">
          <div className="flex h-16 items-center gap-3 border-b border-border px-6">
            <div className="flex size-8 items-center justify-center rounded-md bg-primary text-white">
              <LibraryBig aria-hidden="true" size={17} strokeWidth={2} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight">DocuMind</p>
              <p className="truncate text-[11px] leading-4 text-muted">Research workspace</p>
            </div>
          </div>

          <nav aria-label="Primary" className="flex-1 px-3 py-4">
            <Link
              to="/"
              aria-current="page"
              className="flex h-9 items-center gap-2.5 rounded-md bg-citation px-3 text-sm font-medium text-primary"
            >
              <LayoutDashboard aria-hidden="true" size={16} strokeWidth={2} />
              Overview
            </Link>
          </nav>

          <div className="border-t border-border px-6 py-5">
            <p className="text-xs font-medium text-foreground">Milestone 1</p>
            <p className="mt-1 text-xs leading-5 text-muted">Data foundation</p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="flex h-16 items-center gap-3 border-b border-border bg-surface px-6 md:hidden">
            <div className="flex size-8 items-center justify-center rounded-md bg-primary text-white">
              <LibraryBig aria-hidden="true" size={17} strokeWidth={2} />
            </div>
            <p className="text-sm font-semibold tracking-tight">DocuMind</p>
          </header>

          <div className="mx-auto w-full max-w-[1200px] px-6 py-8 md:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

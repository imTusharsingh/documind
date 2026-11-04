import { BarChart3, FileSearch, FileText, LayoutDashboard, LibraryBig, MessageSquareText, Settings, WalletCards } from 'lucide-react';
import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

import { cn } from '@/lib/utils';

interface AppShellProps {
  children: ReactNode;
}

const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/documents', label: 'Documents', icon: FileText, end: false },
  { to: '/search', label: 'Search', icon: FileSearch, end: false },
  { to: '/chat', label: 'Ask', icon: MessageSquareText, end: false },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3, end: false },
  { to: '/usage', label: 'Usage', icon: WalletCards, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
];

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

          <nav aria-label="Primary" className="flex-1 space-y-1 px-3 py-4">
            {navigation.map((item) => {
              const Icon = item.icon;

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      'flex h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-citation text-primary'
                        : 'text-muted hover:bg-background hover:text-foreground',
                    )
                  }
                >
                  <Icon aria-hidden="true" size={16} strokeWidth={2} />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="border-t border-border px-3 py-4">
            <p className="px-3 pt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">DocuMind workspace</p>
            <p className="px-3 pt-1 text-xs text-muted">Grounded research, in one place.</p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="border-b border-border bg-surface px-6 md:hidden">
            <div className="flex h-16 items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-md bg-primary text-white">
                <LibraryBig aria-hidden="true" size={17} strokeWidth={2} />
              </div>
              <p className="text-sm font-semibold tracking-tight">DocuMind</p>
            </div>
            <nav aria-label="Primary" className="-mx-1 flex gap-1 overflow-x-auto pb-2">
              {navigation.map((item) => {
                const Icon = item.icon;

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      cn(
                        'flex h-8 shrink-0 items-center gap-2 rounded-md px-3 text-xs font-medium transition-colors',
                        isActive
                          ? 'bg-citation text-primary'
                          : 'text-muted hover:bg-background hover:text-foreground',
                      )
                    }
                  >
                    <Icon aria-hidden="true" size={14} strokeWidth={2} />
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </header>

          <div className="mx-auto w-full max-w-[1200px] px-6 py-8 md:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

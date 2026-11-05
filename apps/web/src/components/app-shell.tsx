import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowRight, BarChart3, FileSearch, FileText, LayoutDashboard, MessageSquareText, Settings, UserRound, WalletCards } from 'lucide-react';
import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

import { cn } from '@/lib/utils';
import { BrandLockup, BrandMark } from '@/components/ui';
import { ApiError, fetchCurrentOwner, fetchWorkspaceSettings } from '@/lib/api';

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
  const navigate = useNavigate();
  const ownerQuery = useQuery({ queryKey: ['current-owner'], queryFn: ({ signal }) => fetchCurrentOwner(signal), retry: false });
  const settingsQuery = useQuery({ queryKey: ['workspace-settings'], queryFn: ({ signal }) => fetchWorkspaceSettings(signal) });
  const needsApiKey = settingsQuery.data && !settingsQuery.data.api_key_configured;
  useEffect(() => {
    if (ownerQuery.error instanceof ApiError && ownerQuery.error.status === 401) navigate('/login', { replace: true });
  }, [navigate, ownerQuery.error]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px]">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-border bg-surface/95 backdrop-blur md:flex md:flex-col">
          <div className="flex h-16 items-center gap-3 border-b border-border px-6">
            <NavLink to="/home" aria-label="Open DocuMind home" className="rounded-md focus-visible:outline-none">
              <BrandLockup className="h-9 max-w-[148px]" />
            </NavLink>
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
            <NavLink to="/profile" className={({ isActive }) => cn('mb-3 flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium', isActive ? 'bg-citation text-primary' : 'text-muted hover:bg-background hover:text-foreground')}><UserRound size={16} />Profile</NavLink>
            <p className="px-3 pt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">DocuMind workspace</p>
            <p className="px-3 pt-1 text-xs text-muted">Grounded research, in one place.</p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-border bg-surface/95 px-6 backdrop-blur md:hidden">
            <div className="flex h-16 items-center gap-3">
              <NavLink to="/home" aria-label="Open DocuMind home" className="rounded-md focus-visible:outline-none"><BrandMark /></NavLink>
              <p className="text-sm font-semibold tracking-tight">DocuMind</p>
            </div>
            <NavLink to="/profile" className="mb-2 flex items-center gap-2 text-xs font-medium text-muted"><UserRound size={14} />Profile & sign out</NavLink>
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

          <div className="mx-auto w-full max-w-[1200px] px-6 py-8 md:px-8">
            {needsApiKey ? <div role="status" className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-warning/25 bg-warning/10 px-3.5 py-2.5 text-xs text-warning"><span className="flex min-w-0 items-center gap-2"><AlertTriangle size={15} className="shrink-0" /><span>Configure an API key to enable AI extraction and answers.</span></span><NavLink to="/settings" className="inline-flex shrink-0 items-center gap-1 font-semibold hover:underline">Open settings <ArrowRight size={13} /></NavLink></div> : null}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

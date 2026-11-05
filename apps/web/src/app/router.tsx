import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/app-shell';
import { ChatPage } from './chat-page';
import { EvaluationPage } from './evaluation-page';
import { DocumentsPage } from './documents-page';
import { SearchPage } from './search-page';
import { OverviewPage } from './overview-page';
import { SettingsPage } from './settings-page';
import { UsagePage } from './usage-page';
import { DocsPage } from './docs-page';
import { MarketingPage } from './marketing-page';
import { AuthPage } from './auth-page';
import { ProfilePage } from './profile-page';

export function AppRouter() {
  const hostname = window.location.hostname;
  const homeHost = hostname === 'documind.com' || hostname === 'www.documind.com' || hostname.startsWith('www.') || hostname.startsWith('home.');
  const docsHost = hostname.startsWith('docs.');

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/home" element={<MarketingPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route
          path="/"
          element={
            homeHost ? <MarketingPage /> : docsHost ? <DocsPage /> : <AppShell><OverviewPage /></AppShell>
          }
        />
        <Route
          path="/documents"
          element={
            <AppShell>
              <DocumentsPage />
            </AppShell>
          }
        />
        <Route
          path="/search"
          element={
            <AppShell>
              <SearchPage />
            </AppShell>
          }
        />
        <Route
          path="/chat"
          element={
            <AppShell>
              <ChatPage />
            </AppShell>
          }
        />
        <Route
          path="/evaluation"
          element={
            <AppShell>
              <EvaluationPage />
            </AppShell>
          }
        />
        <Route path="/usage" element={<AppShell><UsagePage /></AppShell>} />
        <Route path="/settings" element={<AppShell><SettingsPage /></AppShell>} />
        <Route path="/profile" element={<AppShell><ProfilePage /></AppShell>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

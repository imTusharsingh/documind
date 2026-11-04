import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/app-shell';
import { ChatPage } from './chat-page';
import { EvaluationPage } from './evaluation-page';
import { DocumentsPage } from './documents-page';
import { SearchPage } from './search-page';
import { OverviewPage } from './overview-page';
import { SettingsPage } from './settings-page';
import { UsagePage } from './usage-page';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <AppShell>
            <OverviewPage />
            </AppShell>
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

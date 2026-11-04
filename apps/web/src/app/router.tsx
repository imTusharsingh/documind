import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/app-shell';
import { ChatPage } from './chat-page';
import { DocumentsPage } from './documents-page';
import { SearchPage } from './search-page';
import { SystemStatusPage } from './system-status-page';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <AppShell>
              <SystemStatusPage />
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

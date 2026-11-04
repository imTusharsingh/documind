import { expect, test } from '@rstest/core';
import { render, screen } from '@testing-library/react';

import {
  DocumentStatusBadge,
  documentStatusLabels,
} from '@/components/document-status-badge';
import type { DocumentStatus } from '@/lib/api';

const statuses: DocumentStatus[] = ['pending', 'processing', 'ready', 'failed'];

for (const status of statuses) {
  test(`renders the ${status} status label`, () => {
    render(<DocumentStatusBadge status={status} />);

    expect(screen.getByRole('status')).toHaveTextContent(documentStatusLabels[status]);
  });
}

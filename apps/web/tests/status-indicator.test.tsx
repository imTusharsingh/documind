import { expect, test } from '@rstest/core';
import { render, screen } from '@testing-library/react';

import { StatusIndicator } from '@/components/status-indicator';

test('renders an online status with its label', () => {
  render(<StatusIndicator status="online" label="API online" />);

  expect(screen.getByRole('status')).toHaveTextContent('API online');
});

test('renders an offline status with its label', () => {
  render(<StatusIndicator status="offline" label="API unreachable" />);

  expect(screen.getByRole('status')).toHaveTextContent('API unreachable');
});

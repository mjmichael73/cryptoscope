import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AlertRules from './AlertRules';

const { listAlertRules, listSymbols, listAlertTemplates, createAlertRule, deleteAlertRule } = vi.hoisted(() => ({
  listAlertRules: vi.fn(), listSymbols: vi.fn(), listAlertTemplates: vi.fn(),
  createAlertRule: vi.fn(), deleteAlertRule: vi.fn(),
}));
vi.mock('../api/client', () => ({ client: { listAlertRules, listSymbols, listAlertTemplates, createAlertRule, deleteAlertRule } }));

const rule = {
  id: 'rule-1', tenant_id: 'tenant-1', symbol: 'BTCUSDT', comparator: 'above' as const,
  threshold: 65000, status: 'active', created_at: '2026-11-14T12:00:00Z', updated_at: '2026-11-14T12:00:00Z',
  interval: '5m', window_seconds: null, cooldown_seconds: 300,
};

beforeEach(() => {
  listAlertRules.mockReset().mockResolvedValue([rule]);
  listSymbols.mockReset().mockResolvedValue({ symbols: ['BTCUSDT'] });
  listAlertTemplates.mockReset().mockResolvedValue([]);
  createAlertRule.mockReset().mockResolvedValue({ id: 'rule-2' });
  deleteAlertRule.mockReset().mockResolvedValue(undefined);
  vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
});

describe('AlertRules page', () => {
  it('renders fetched rules in the rules table', async () => {
    render(<AlertRules />);
    expect(await screen.findByRole('table', { name: 'Alert rules' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Symbol' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'BTCUSDT' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'Above' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '65000' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '5m' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'active' })).toBeInTheDocument();
  });

  it('deletes after confirmation and reloads rules', async () => {
    const user = userEvent.setup();
    render(<AlertRules />);
    await screen.findByRole('table', { name: 'Alert rules' });
    await user.click(screen.getByRole('button', { name: 'Delete rule for BTCUSDT' }));
    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => expect(deleteAlertRule).toHaveBeenCalledWith('rule-1'));
    await waitFor(() => expect(listAlertRules).toHaveBeenCalledTimes(2));
  });

  it('shows the empty state when there are no rules', async () => {
    listAlertRules.mockResolvedValue([]);
    render(<AlertRules />);
    expect(await screen.findByText('No alert rules configured.')).toBeInTheDocument();
  });
});

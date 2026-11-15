import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AlertTriggers from './AlertTriggers';

const { listTriggers, ackTrigger, clearTriggers } = vi.hoisted(() => ({ listTriggers: vi.fn(), ackTrigger: vi.fn(), clearTriggers: vi.fn() }));
vi.mock('../api/client', () => ({ client: { listTriggers, ackTrigger, clearTriggers } }));

const triggers = [
  { id: 'trg-1', tenant_id: 'tenant-1', rule_id: 'rule-1', symbol: 'BTCUSDT', comparator: 'above', threshold: 65000, current_value: 66000, triggered_at: '2026-11-14T12:00:00Z', acknowledged: true, interval: '5m', window_seconds: null },
  { id: 'trg-2', tenant_id: 'tenant-1', rule_id: 'rule-2', symbol: 'ETHUSDT', comparator: 'below', threshold: 3000, current_value: 2900, triggered_at: '2026-11-14T13:00:00Z', acknowledged: false, interval: '1m', window_seconds: null },
];

beforeEach(() => {
  listTriggers.mockReset().mockResolvedValue(triggers);
  ackTrigger.mockReset();
  clearTriggers.mockReset().mockResolvedValue({ deleted: 1 });
  vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
});

describe('AlertTriggers page', () => {
  it('clears acknowledged history and reloads', async () => {
    const user = userEvent.setup();
    render(<AlertTriggers />);
    await screen.findByText('BTCUSDT');
    await user.click(screen.getByRole('button', { name: 'Clear acknowledged' }));
    expect(clearTriggers).toHaveBeenCalledWith(true);
    await waitFor(() => expect(listTriggers).toHaveBeenCalledTimes(2));
  });

  it('confirms before clearing all history and reloads', async () => {
    const user = userEvent.setup();
    render(<AlertTriggers />);
    await screen.findByText('BTCUSDT');
    await user.click(screen.getByRole('button', { name: 'Clear all' }));
    expect(window.confirm).toHaveBeenCalled();
    expect(clearTriggers).toHaveBeenCalledWith(false);
    await waitFor(() => expect(listTriggers).toHaveBeenCalledTimes(2));
  });

  it('hides clear actions when no matching history exists', async () => {
    listTriggers.mockResolvedValue([]);
    render(<AlertTriggers />);
    await screen.findByText('No triggers recorded yet.');
    expect(screen.queryByRole('button', { name: 'Clear acknowledged' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Clear all' })).not.toBeInTheDocument();
  });
});

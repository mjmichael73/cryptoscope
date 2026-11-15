import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Watchlists from './Watchlists';

const { listWatchlists, listSymbols, createWatchlist, updateWatchlist, deleteWatchlist } = vi.hoisted(() => ({
  listWatchlists: vi.fn(),
  listSymbols: vi.fn(),
  createWatchlist: vi.fn(),
  updateWatchlist: vi.fn(),
  deleteWatchlist: vi.fn(),
}));
vi.mock('../api/client', () => ({ client: { listWatchlists, listSymbols, createWatchlist, updateWatchlist, deleteWatchlist } }));

const watchlist = { id: 'wl-1', tenant_id: 'tenant-1', name: 'Core assets', symbols: ['BTCUSDT', 'ETHUSDT'], created_at: '2026-11-14T12:00:00Z' };

beforeEach(() => {
  listWatchlists.mockReset().mockResolvedValue([watchlist]);
  listSymbols.mockReset().mockResolvedValue({ symbols: ['BTCUSDT', 'ETHUSDT'] });
  createWatchlist.mockReset().mockResolvedValue({ id: 'wl-2' });
  updateWatchlist.mockReset().mockResolvedValue(watchlist);
  deleteWatchlist.mockReset().mockResolvedValue(undefined);
  vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
});

describe('Watchlists page', () => {
  it('renders fetched watchlists and their symbols', async () => {
    render(<Watchlists />);
    expect(await screen.findByRole('heading', { name: 'Core assets' })).toBeInTheDocument();
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
    expect(listWatchlists).toHaveBeenCalledTimes(1);
  });

  it('creates a watchlist and reloads the list', async () => {
    const user = userEvent.setup();
    render(<Watchlists />);
    await screen.findByRole('heading', { name: 'Core assets' });
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Long term');
    await user.type(screen.getByRole('textbox', { name: 'Symbols (comma-separated)' }), ' solusdt, btcusdt ');
    await user.click(screen.getByRole('button', { name: 'Create Watchlist' }));
    await waitFor(() => expect(createWatchlist).toHaveBeenCalledWith('Long term', ['SOLUSDT', 'BTCUSDT']));
    await waitFor(() => expect(listWatchlists).toHaveBeenCalledTimes(2));
  });

  it('edits a watchlist name and symbols', async () => {
    const user = userEvent.setup();
    render(<Watchlists />);
    await screen.findByRole('heading', { name: 'Core assets' });
    await user.click(screen.getByRole('button', { name: 'Edit Core assets' }));
    await user.clear(screen.getByRole('textbox', { name: 'Edit name for Core assets' }));
    await user.type(screen.getByRole('textbox', { name: 'Edit name for Core assets' }), 'Core + DeFi');
    await user.clear(screen.getByRole('textbox', { name: 'Edit symbols for Core assets' }));
    await user.type(screen.getByRole('textbox', { name: 'Edit symbols for Core assets' }), 'ETHUSDT, SOLUSDT');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(updateWatchlist).toHaveBeenCalledWith('wl-1', 'Core + DeFi', ['ETHUSDT', 'SOLUSDT']));
  });

  it('deletes a watchlist after confirmation', async () => {
    const user = userEvent.setup();
    render(<Watchlists />);
    await screen.findByRole('heading', { name: 'Core assets' });
    await user.click(screen.getByRole('button', { name: 'Delete Core assets' }));
    expect(window.confirm).toHaveBeenCalled();
    expect(deleteWatchlist).toHaveBeenCalledWith('wl-1');
  });

  it('shows API errors', async () => {
    listWatchlists.mockRejectedValue(new Error('backend unavailable'));
    render(<Watchlists />);
    expect(await screen.findByText('backend unavailable')).toBeInTheDocument();
  });
});

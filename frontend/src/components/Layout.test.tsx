import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Layout from './Layout';

const { logout } = vi.hoisted(() => ({ logout: vi.fn() }));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { username: 'mira' }, logout }) }));

beforeEach(() => logout.mockClear());

describe('Layout', () => {
  it('shows the authenticated username and logs out', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(screen.getByText('mira')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Logout' }));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it('toggles the mobile navigation drawer', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Layout /></MemoryRouter>);
    const toggle = screen.getByRole('button', { name: 'Open navigation' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(screen.getByRole('dialog', { name: 'Mobile navigation' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Close navigation' })).toHaveAttribute('aria-expanded', 'true');
    await user.click(screen.getByRole('button', { name: 'Close navigation' }));
    expect(screen.queryByRole('dialog', { name: 'Mobile navigation' })).not.toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Login from './Login';

const { loginMock, loginDemoMock } = vi.hoisted(() => ({ loginMock: vi.fn(), loginDemoMock: vi.fn() }));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ login: loginMock, loginDemo: loginDemoMock }) }));

beforeEach(() => {
  loginMock.mockClear();
  loginDemoMock.mockClear();
});

describe('Login', () => {
  it('offers Keycloak sign in', async () => {
    render(<MemoryRouter><Login /></MemoryRouter>);
    await userEvent.click(screen.getByRole('button', { name: /sign in with keycloak/i }));
    expect(loginMock).toHaveBeenCalled();
  });

  it('shows demo login only when development auth is enabled', () => {
    vi.stubEnv('VITE_DEV_AUTH', '1');
    const { unmount } = render(<MemoryRouter><Login /></MemoryRouter>);
    expect(screen.getByRole('button', { name: /demo login/i })).toBeInTheDocument();
    unmount();
    vi.stubEnv('VITE_DEV_AUTH', '0');
    render(<MemoryRouter><Login /></MemoryRouter>);
    expect(screen.queryByRole('button', { name: /demo login/i })).not.toBeInTheDocument();
  });
});

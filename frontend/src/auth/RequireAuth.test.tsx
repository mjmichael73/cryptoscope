import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import RequireAuth from './RequireAuth';

function LocationProbe() {
  const location = useLocation();
  return <p>login from {String((location.state as { from?: { pathname?: string } } | null)?.from?.pathname)}</p>;
}

describe('RequireAuth', () => {
  it('redirects unauthenticated visitors to login with the original route', async () => {
    vi.stubEnv('VITE_DEV_AUTH', '0');
    sessionStorage.clear();
    render(<MemoryRouter initialEntries={['/watchlists']}>
      <AuthProvider><Routes>
        <Route path="/login" element={<LocationProbe />} />
        <Route element={<RequireAuth />}><Route path="/watchlists" element={<p>private</p>} /></Route>
      </Routes></AuthProvider>
    </MemoryRouter>);
    expect(await screen.findByText('login from /watchlists')).toBeInTheDocument();
  });
});

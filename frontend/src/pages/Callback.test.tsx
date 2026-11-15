import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Callback from './Callback';
import { AuthProvider } from '../auth/AuthContext';

const { mockedExchangeCode, mockedDecodeJwt } = vi.hoisted(() => ({ mockedExchangeCode: vi.fn(), mockedDecodeJwt: vi.fn() }));
vi.mock('../auth/oidc', () => ({
  oidcConfigFromEnv: () => ({ issuer: '/auth/realms/cryptoscope', clientId: 'client' }),
  exchangeCode: mockedExchangeCode,
  decodeJwt: mockedDecodeJwt,
}));

beforeEach(() => {
  sessionStorage.clear();
  mockedExchangeCode.mockReset().mockResolvedValue({ access_token: 'access', refresh_token: 'refresh', expires_in: 600, id_token: 'id' });
  mockedDecodeJwt.mockReset().mockReturnValue({ preferred_username: 'mira' });
});

describe('Callback', () => {
  it('shows an error when OAuth state does not match', async () => {
    sessionStorage.setItem('cryptoscope.auth.oauth_state', 'expected');
    render(<MemoryRouter initialEntries={['/callback?code=abc&state=wrong']}><AuthProvider><Callback /></AuthProvider></MemoryRouter>);
    expect(await screen.findByText(/could not verify sign-in request/i)).toBeInTheDocument();
    expect(mockedExchangeCode).not.toHaveBeenCalled();
  });

  it.each([
    ['invalid_scope', /sign-in provider is not configured correctly/i],
    ['access_denied', /sign-in was cancelled or denied/i],
    ['server_error', /sign-in provider could not complete this request/i],
  ])('reports a verified provider error (%s) without exchanging a code', async (error, message) => {
    sessionStorage.setItem('cryptoscope.auth.oauth_state', 'expected');
    sessionStorage.setItem('cryptoscope.auth.pkce_verifier', 'verifier');
    render(<MemoryRouter initialEntries={[`/callback?error=${error}&state=expected`]}><AuthProvider><Callback /></AuthProvider></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(mockedExchangeCode).not.toHaveBeenCalled();
    expect(sessionStorage.getItem('cryptoscope.auth.oauth_state')).toBeNull();
    expect(sessionStorage.getItem('cryptoscope.auth.pkce_verifier')).toBeNull();
    expect(sessionStorage.getItem('cryptoscope.auth.access_token')).toBeNull();
  });

  it('rejects a provider error with mismatched state', async () => {
    sessionStorage.setItem('cryptoscope.auth.oauth_state', 'expected');
    sessionStorage.setItem('cryptoscope.auth.pkce_verifier', 'verifier');
    render(<MemoryRouter initialEntries={['/callback?error=invalid_scope&state=wrong']}><AuthProvider><Callback /></AuthProvider></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not verify sign-in request/i);
    expect(mockedExchangeCode).not.toHaveBeenCalled();
    expect(sessionStorage.getItem('cryptoscope.auth.oauth_state')).toBe('expected');
  });

  it('exchanges a valid code and navigates to the stored destination', async () => {
    sessionStorage.setItem('cryptoscope.auth.oauth_state', 'expected');
    sessionStorage.setItem('cryptoscope.auth.pkce_verifier', 'verifier');
    sessionStorage.setItem('cryptoscope.auth.return_to', '/watchlists');
    render(<MemoryRouter initialEntries={['/callback?code=abc&state=expected']}><AuthProvider><Routes>
      <Route path="/callback" element={<Callback />} />
      <Route path="/watchlists" element={<p>watchlists destination</p>} />
    </Routes></AuthProvider></MemoryRouter>);
    expect(await screen.findByText('watchlists destination')).toBeInTheDocument();
    expect(mockedExchangeCode).toHaveBeenCalledWith(expect.anything(), 'abc', 'verifier', `${window.location.origin}/callback`);
    expect(sessionStorage.getItem('cryptoscope.auth.access_token')).toBe('access');
  });
});

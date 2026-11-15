import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import RequireAuth from './auth/RequireAuth';
import Layout from './components/Layout';
import AlertRules from './pages/AlertRules';
import AlertTriggers from './pages/AlertTriggers';
import Callback from './pages/Callback';
import Dashboard from './pages/Dashboard';
import Health from './pages/Health';
import Login from './pages/Login';
import MarketData from './pages/MarketData';
import Watchlists from './pages/Watchlists';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/callback" element={<Callback />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="/market-data" element={<MarketData />} />
            <Route path="/watchlists" element={<Watchlists />} />
            <Route path="/alert-rules" element={<AlertRules />} />
            <Route path="/triggers" element={<AlertTriggers />} />
            <Route path="/health" element={<Health />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  </BrowserRouter>,
);

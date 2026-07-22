import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AlertRules from "./pages/AlertRules";
import AlertTriggers from "./pages/AlertTriggers";
import Dashboard from "./pages/Dashboard";
import Health from "./pages/Health";
import MarketData from "./pages/MarketData";
import Watchlists from "./pages/Watchlists";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/market-data" element={<MarketData />} />
        <Route path="/watchlists" element={<Watchlists />} />
        <Route path="/alert-rules" element={<AlertRules />} />
        <Route path="/triggers" element={<AlertTriggers />} />
        <Route path="/health" element={<Health />} />
      </Route>
    </Routes>
  </BrowserRouter>,
);

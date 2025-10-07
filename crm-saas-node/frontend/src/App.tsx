import { Routes, Route } from 'react-router-dom';
import { PrivateRoute } from './components/PrivateRoute';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { LeadsPage } from './pages/LeadsPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { DealsPage } from './pages/DealsPage';
import { DealDetailPage } from './pages/DealDetailPage';
import { InvoicesPage } from './pages/InvoicesPage';
import { InvoiceDetailPage } from './pages/InvoiceDetailPage';
import { AssetsPage } from './pages/AssetsPage';

function App() {
  return (
    <Routes>
      <Route element={<PrivateRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="leads" element={<LeadsPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="deals" element={<DealsPage />} />
          <Route path="deals/:id" element={<DealDetailPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="invoices/:id" element={<InvoiceDetailPage />} />
          <Route path="assets" element={<AssetsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;

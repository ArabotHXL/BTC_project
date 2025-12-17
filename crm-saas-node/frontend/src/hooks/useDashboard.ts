import { useState, useEffect } from 'react';
import api from '../lib/api';
import { DashboardMetrics, Lead, Deal, Invoice, Asset } from '../types';

export const useDashboard = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const leadsResponse = await api.get<Lead[]>('/api/leads');
        const dealsResponse = await api.get<Deal[]>('/api/deals');
        const invoicesResponse = await api.get<Invoice[]>('/api/invoices');
        const assetsResponse = await api.get<Asset[]>('/api/assets');

        setMetrics({
          totalLeads: leadsResponse.data.length,
          activeDeals: dealsResponse.data.filter((d: Deal) => 
            !['CLOSED_WON', 'CLOSED_LOST'].includes(d.stage)
          ).length,
          pendingInvoices: invoicesResponse.data.filter((i: Invoice) => 
            i.status !== 'PAID'
          ).length,
          totalAssets: assetsResponse.data.length,
        });
        setError(null);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch metrics';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  return { metrics, loading, error };
};

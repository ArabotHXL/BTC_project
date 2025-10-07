import React from 'react';
import { useTranslation } from 'react-i18next';
import { useDashboard } from '../hooks/useDashboard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';

export const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { metrics, loading, error } = useDashboard();

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">{t('dashboard.dashboard')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-gray-400">{t('dashboard.totalLeads')}</h3>
            <span className="text-2xl">👥</span>
          </div>
          <p className="text-3xl font-bold text-amber-500">{metrics?.totalLeads || 0}</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-gray-400">{t('dashboard.activeDeals')}</h3>
            <span className="text-2xl">💼</span>
          </div>
          <p className="text-3xl font-bold text-amber-500">{metrics?.activeDeals || 0}</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-gray-400">{t('dashboard.pendingInvoices')}</h3>
            <span className="text-2xl">🧾</span>
          </div>
          <p className="text-3xl font-bold text-amber-500">{metrics?.pendingInvoices || 0}</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-gray-400">{t('dashboard.totalAssets')}</h3>
            <span className="text-2xl">🏗️</span>
          </div>
          <p className="text-3xl font-bold text-amber-500">{metrics?.totalAssets || 0}</p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-bold text-white mb-4">{t('dashboard.overview')}</h2>
        <p className="text-gray-400">
          Welcome to your CRM dashboard. Use the navigation menu to manage leads, deals, invoices, and assets.
        </p>
      </div>
    </div>
  );
};

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAssets } from '../hooks/useAssets';
import { Table } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';

export const AssetsPage: React.FC = () => {
  const { t } = useTranslation();
  const { assets, loading, error } = useAssets();

  const columns = [
    { key: 'serialNumber', header: t('asset.serialNumber') },
    { key: 'model', header: t('asset.model') },
    { 
      key: 'status', 
      header: t('common.status'),
      render: (asset: any) => (
        <span className={`px-2 py-1 rounded text-xs ${
          asset.status === 'ACTIVE' ? 'bg-green-600' : 
          asset.status === 'SHIPPED' ? 'bg-blue-600' : 
          'bg-gray-600'
        }`}>
          {asset.status}
        </span>
      )
    },
    { 
      key: 'purchaseDate', 
      header: t('asset.purchaseDate'),
      render: (asset: any) => asset.purchaseDate ? new Date(asset.purchaseDate).toLocaleDateString() : '-'
    },
  ];

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">{t('asset.assets')}</h1>

      <Table columns={columns} data={assets} />
    </div>
  );
};

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useInvoices } from '../hooks/useInvoices';
import { Table } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';

export const InvoicesPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { invoices, loading, error } = useInvoices();

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      DRAFT: 'bg-gray-600',
      SENT: 'bg-blue-600',
      PARTIAL: 'bg-yellow-600',
      PAID: 'bg-green-600',
      OVERDUE: 'bg-red-600',
    };
    return (
      <span className={`px-2 py-1 rounded text-xs ${colors[status] || 'bg-gray-600'}`}>
        {t(`invoice.statuses.${status}`)}
      </span>
    );
  };

  const columns = [
    { key: 'invoiceNumber', header: t('invoice.invoiceNumber') },
    { 
      key: 'totalAmount', 
      header: t('common.amount'),
      render: (invoice: any) => `$${invoice.totalAmount.toLocaleString()}`
    },
    { 
      key: 'status', 
      header: t('common.status'),
      render: (invoice: any) => getStatusBadge(invoice.status)
    },
    { 
      key: 'dueDate', 
      header: t('invoice.dueDate'),
      render: (invoice: any) => new Date(invoice.dueDate).toLocaleDateString()
    },
  ];

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">{t('invoice.invoices')}</h1>

      <Table
        columns={columns}
        data={invoices}
        onRowClick={(invoice) => navigate(`/invoices/${invoice.id}`)}
      />
    </div>
  );
};

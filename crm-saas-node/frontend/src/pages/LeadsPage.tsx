import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLeads } from '../hooks/useLeads';
import { Lead } from '../types';
import { Table } from '../components/ui/Table';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { Modal } from '../components/ui/Modal';
import { LeadForm } from '../components/leads/LeadForm';

export const LeadsPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { leads, loading, error, createLead, refetch } = useLeads();
  const [showModal, setShowModal] = useState(false);
  const [success, setSuccess] = useState('');

  const handleCreateLead = async (data: Partial<Lead>) => {
    try {
      await createLead(data);
      setShowModal(false);
      setSuccess('Lead created successfully');
      refetch();
    } catch (err) {
      console.error('Failed to create lead:', err);
    }
  };

  const columns = [
    { key: 'name', header: t('common.name') },
    { key: 'email', header: t('common.email') },
    { key: 'company', header: t('common.company') },
    { 
      key: 'source', 
      header: t('lead.source'),
      render: (lead: Lead) => t(`lead.sources.${lead.source}`)
    },
    { 
      key: 'score', 
      header: t('lead.score'),
      render: (lead: Lead) => <span className="text-amber-500">{lead.score || 0}</span>
    },
  ];

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">{t('lead.leads')}</h1>
        <Button onClick={() => setShowModal(true)}>{t('lead.newLead')}</Button>
      </div>

      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

      <Table
        columns={columns}
        data={leads}
        onRowClick={(lead) => navigate(`/leads/${lead.id}`)}
      />

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={t('lead.newLead')}>
        <LeadForm onSubmit={handleCreateLead} onCancel={() => setShowModal(false)} />
      </Modal>
    </div>
  );
};

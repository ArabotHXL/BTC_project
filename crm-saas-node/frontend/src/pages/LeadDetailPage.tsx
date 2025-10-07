import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLeadDetail } from '../hooks/useLeads';
import { useLeads } from '../hooks/useLeads';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';

export const LeadDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { lead, loading, error } = useLeadDetail(id!);
  const { convertToDeal } = useLeads();
  const [converting, setConverting] = useState(false);
  const [success, setSuccess] = useState('');

  const handleConvert = async () => {
    try {
      setConverting(true);
      await convertToDeal(Number(id));
      setSuccess(t('lead.leadConverted'));
      setTimeout(() => navigate('/deals'), 2000);
    } catch (err) {
      console.error('Failed to convert lead:', err);
    } finally {
      setConverting(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;
  if (!lead) return <Alert type="error" message="Lead not found" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">{t('lead.leadDetails')}</h1>
        <div className="flex space-x-2">
          <Button variant="secondary" onClick={() => navigate('/leads')}>
            {t('common.back')}
          </Button>
          <Button onClick={handleConvert} isLoading={converting}>
            {t('lead.convertToDeal')}
          </Button>
        </div>
      </div>

      {success && <Alert type="success" message={success} />}

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-gray-400 text-sm">{t('common.name')}</p>
            <p className="text-white text-lg">{lead.name}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('common.email')}</p>
            <p className="text-white text-lg">{lead.email}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('common.phone')}</p>
            <p className="text-white text-lg">{lead.phone || '-'}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('common.company')}</p>
            <p className="text-white text-lg">{lead.company || '-'}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('lead.source')}</p>
            <p className="text-white text-lg">{t(`lead.sources.${lead.source}`)}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('lead.score')}</p>
            <p className="text-amber-500 text-lg font-bold">{lead.score || 0}</p>
          </div>
        </div>
        {lead.notes && (
          <div className="mt-4">
            <p className="text-gray-400 text-sm">{t('common.notes')}</p>
            <p className="text-white">{lead.notes}</p>
          </div>
        )}
      </div>
    </div>
  );
};

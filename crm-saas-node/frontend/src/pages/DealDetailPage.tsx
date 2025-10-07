import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useDealDetail, useDeals } from '../hooks/useDeals';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';

export const DealDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { deal, loading, error } = useDealDetail(id!);
  const { updateDealStage, generateContract } = useDeals();
  const [newStage, setNewStage] = useState('');
  const [updating, setUpdating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [success, setSuccess] = useState('');

  const handleStageChange = async () => {
    if (!newStage) return;
    try {
      setUpdating(true);
      await updateDealStage(Number(id), newStage);
      setSuccess('Deal stage updated successfully');
      window.location.reload();
    } catch (err) {
      console.error('Failed to update stage:', err);
    } finally {
      setUpdating(false);
    }
  };

  const handleGenerateContract = async () => {
    try {
      setGenerating(true);
      const contract = await generateContract(Number(id));
      setSuccess(`Contract generated: ${contract.contractNumber}`);
    } catch (err) {
      console.error('Failed to generate contract:', err);
    } finally {
      setGenerating(false);
    }
  };

  const stageOptions = [
    { value: 'PROSPECTING', label: t('deal.stages.PROSPECTING') },
    { value: 'QUALIFIED', label: t('deal.stages.QUALIFIED') },
    { value: 'PROPOSAL', label: t('deal.stages.PROPOSAL') },
    { value: 'NEGOTIATION', label: t('deal.stages.NEGOTIATION') },
    { value: 'CLOSED_WON', label: t('deal.stages.CLOSED_WON') },
    { value: 'CLOSED_LOST', label: t('deal.stages.CLOSED_LOST') },
  ];

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;
  if (!deal) return <Alert type="error" message="Deal not found" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">{t('deal.dealDetails')}</h1>
        <div className="flex space-x-2">
          <Button variant="secondary" onClick={() => navigate('/deals')}>
            {t('common.back')}
          </Button>
          <Button onClick={handleGenerateContract} isLoading={generating}>
            {t('deal.generateContract')}
          </Button>
        </div>
      </div>

      {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-gray-400 text-sm">{t('common.name')}</p>
            <p className="text-white text-lg">{deal.title}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('deal.value')}</p>
            <p className="text-amber-500 text-lg font-bold">${deal.value.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('deal.stage')}</p>
            <p className="text-white text-lg">{t(`deal.stages.${deal.stage}`)}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('deal.probability')}</p>
            <p className="text-white text-lg">{deal.probability}%</p>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-white text-lg mb-4">Update Stage</h3>
        <div className="flex space-x-2">
          <div className="flex-1">
            <Select
              options={stageOptions}
              value={newStage}
              onChange={(e) => setNewStage(e.target.value)}
            />
          </div>
          <Button onClick={handleStageChange} isLoading={updating}>
            {t('common.save')}
          </Button>
        </div>
      </div>
    </div>
  );
};

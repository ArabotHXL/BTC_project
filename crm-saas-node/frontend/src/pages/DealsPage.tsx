import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useDeals } from '../hooks/useDeals';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';

export const DealsPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { deals, loading, error, updateDealStage } = useDeals();

  const stages = ['PROSPECTING', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'CLOSED_WON', 'CLOSED_LOST'];

  const getDealsByStage = (stage: string) => {
    return deals.filter((deal) => deal.stage === stage);
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">{t('deal.pipeline')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stages.map((stage) => (
          <div key={stage} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">
              {t(`deal.stages.${stage}`)}
            </h3>
            <div className="space-y-2">
              {getDealsByStage(stage).map((deal) => (
                <div
                  key={deal.id}
                  onClick={() => navigate(`/deals/${deal.id}`)}
                  className="bg-gray-700 p-3 rounded cursor-pointer hover:bg-gray-600 transition-colors"
                >
                  <p className="text-white font-medium text-sm">{deal.title}</p>
                  <p className="text-amber-500 text-xs mt-1">${deal.value.toLocaleString()}</p>
                  {deal.probability && (
                    <p className="text-gray-400 text-xs">{deal.probability}% chance</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

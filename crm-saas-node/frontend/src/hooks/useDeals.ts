import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Deal } from '../types';

export const useDeals = () => {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDeals = async () => {
    try {
      setLoading(true);
      const response = await api.get<Deal[]>('/api/deals');
      setDeals(response.data);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch deals';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, []);

  const createDeal = async (data: Partial<Deal>) => {
    const response = await api.post<Deal>('/api/deals', data);
    await fetchDeals();
    return response.data;
  };

  const updateDealStage = async (id: number, stage: string) => {
    const response = await api.put<Deal>(`/api/deals/${id}/stage`, { stage });
    await fetchDeals();
    return response.data;
  };

  const generateContract = async (id: number) => {
    const response = await api.post(`/api/deals/${id}/generate-contract`);
    return response.data;
  };

  return { deals, loading, error, createDeal, updateDealStage, generateContract, refetch: fetchDeals };
};

export const useDealDetail = (id: string) => {
  const [deal, setDeal] = useState<Deal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDeal = async () => {
      try {
        setLoading(true);
        const response = await api.get<Deal>(`/api/deals/${id}`);
        setDeal(response.data);
        setError(null);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch deal';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchDeal();
    }
  }, [id]);

  return { deal, loading, error };
};

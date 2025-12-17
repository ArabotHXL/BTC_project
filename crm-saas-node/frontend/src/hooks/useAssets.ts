import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Asset } from '../types';

export const useAssets = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const response = await api.get<Asset[]>('/api/assets');
      setAssets(response.data);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch assets';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  return { assets, loading, error, refetch: fetchAssets };
};

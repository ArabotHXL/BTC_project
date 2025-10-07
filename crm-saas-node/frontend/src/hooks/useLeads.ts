import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Lead, ApiResponse } from '../types';

export const useLeads = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const response = await api.get<Lead[]>('/api/leads');
      setLeads(response.data);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch leads';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const createLead = async (data: Partial<Lead>) => {
    const response = await api.post<Lead>('/api/leads', data);
    await fetchLeads();
    return response.data;
  };

  const updateLead = async (id: number, data: Partial<Lead>) => {
    const response = await api.put<Lead>(`/api/leads/${id}`, data);
    await fetchLeads();
    return response.data;
  };

  const convertToDeal = async (id: number) => {
    const response = await api.post(`/api/leads/${id}/convert-to-deal`);
    await fetchLeads();
    return response.data;
  };

  return { leads, loading, error, createLead, updateLead, convertToDeal, refetch: fetchLeads };
};

export const useLeadDetail = (id: string) => {
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLead = async () => {
      try {
        setLoading(true);
        const response = await api.get<Lead>(`/api/leads/${id}`);
        setLead(response.data);
        setError(null);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch lead';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchLead();
    }
  }, [id]);

  return { lead, loading, error };
};

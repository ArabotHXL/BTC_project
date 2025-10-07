import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Invoice, Payment } from '../types';

export const useInvoices = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const response = await api.get<Invoice[]>('/api/invoices');
      setInvoices(response.data);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch invoices';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const recordPayment = async (invoiceId: number, data: Partial<Payment>) => {
    const response = await api.post<Payment>(`/api/invoices/${invoiceId}/payments`, data);
    await fetchInvoices();
    return response.data;
  };

  return { invoices, loading, error, recordPayment, refetch: fetchInvoices };
};

export const useInvoiceDetail = (id: string) => {
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInvoice = async () => {
      try {
        setLoading(true);
        const response = await api.get<Invoice>(`/api/invoices/${id}`);
        setInvoice(response.data);
        setError(null);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch invoice';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchInvoice();
    }
  }, [id]);

  return { invoice, loading, error };
};

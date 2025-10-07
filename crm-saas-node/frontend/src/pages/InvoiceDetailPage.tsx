import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useInvoiceDetail, useInvoices } from '../hooks/useInvoices';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PaymentForm } from '../components/invoices/PaymentForm';

export const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { invoice, loading, error } = useInvoiceDetail(id!);
  const { recordPayment } = useInvoices();
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [success, setSuccess] = useState('');

  const handleRecordPayment = async (data: any) => {
    try {
      await recordPayment(Number(id), data);
      setShowPaymentModal(false);
      setSuccess(t('invoice.paymentRecorded'));
      window.location.reload();
    } catch (err) {
      console.error('Failed to record payment:', err);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert type="error" message={error} />;
  if (!invoice) return <Alert type="error" message="Invoice not found" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">{t('invoice.invoiceDetails')}</h1>
        <div className="flex space-x-2">
          <Button variant="secondary" onClick={() => navigate('/invoices')}>
            {t('common.back')}
          </Button>
          <Button onClick={() => setShowPaymentModal(true)}>
            {t('invoice.recordPayment')}
          </Button>
        </div>
      </div>

      {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-gray-400 text-sm">{t('invoice.invoiceNumber')}</p>
            <p className="text-white text-lg">{invoice.invoiceNumber}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('common.amount')}</p>
            <p className="text-amber-500 text-lg font-bold">${invoice.totalAmount.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('common.status')}</p>
            <p className="text-white text-lg">{t(`invoice.statuses.${invoice.status}`)}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">{t('invoice.dueDate')}</p>
            <p className="text-white text-lg">{new Date(invoice.dueDate).toLocaleDateString()}</p>
          </div>
        </div>

        {invoice.payments && invoice.payments.length > 0 && (
          <div className="mt-6">
            <h3 className="text-white text-lg mb-3">Payment History</h3>
            <div className="space-y-2">
              {invoice.payments.map((payment: any) => (
                <div key={payment.id} className="bg-gray-700 p-3 rounded flex justify-between">
                  <span className="text-gray-300">${payment.amount.toLocaleString()}</span>
                  <span className="text-gray-400">{new Date(payment.paymentDate).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <Modal isOpen={showPaymentModal} onClose={() => setShowPaymentModal(false)} title={t('invoice.recordPayment')}>
        <PaymentForm onSubmit={handleRecordPayment} onCancel={() => setShowPaymentModal(false)} />
      </Modal>
    </div>
  );
};

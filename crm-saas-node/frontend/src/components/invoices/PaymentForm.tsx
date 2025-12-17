import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { paymentSchema, PaymentFormData } from '../../schemas/paymentSchema';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';

interface PaymentFormProps {
  onSubmit: (data: PaymentFormData) => Promise<void>;
  onCancel: () => void;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({ onSubmit, onCancel }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<Partial<PaymentFormData>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    try {
      const validData = paymentSchema.parse({
        ...formData,
        amount: Number(formData.amount),
      });
      setLoading(true);
      await onSubmit(validData);
    } catch (err: any) {
      if (err.errors) {
        const fieldErrors: Record<string, string> = {};
        err.errors.forEach((error: any) => {
          fieldErrors[error.path[0]] = error.message;
        });
        setErrors(fieldErrors);
      }
    } finally {
      setLoading(false);
    }
  };

  const methodOptions = [
    { value: 'CASH', label: t('payment.methods.CASH') },
    { value: 'BANK_TRANSFER', label: t('payment.methods.BANK_TRANSFER') },
    { value: 'CREDIT_CARD', label: t('payment.methods.CREDIT_CARD') },
    { value: 'CHECK', label: t('payment.methods.CHECK') },
  ];

  return (
    <form onSubmit={handleSubmit}>
      <Input
        type="number"
        step="0.01"
        label={t('payment.paymentAmount')}
        value={formData.amount || ''}
        onChange={(e) => setFormData({ ...formData, amount: e.target.value as any })}
        error={errors.amount}
      />
      <Select
        label={t('payment.paymentMethod')}
        options={methodOptions}
        value={formData.paymentMethod || ''}
        onChange={(e) => setFormData({ ...formData, paymentMethod: e.target.value as any })}
        error={errors.paymentMethod}
      />
      <Input
        type="date"
        label={t('payment.paymentDate')}
        value={formData.paymentDate || ''}
        onChange={(e) => setFormData({ ...formData, paymentDate: e.target.value })}
        error={errors.paymentDate}
      />
      <Input
        label={t('common.notes')}
        value={formData.notes || ''}
        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
        error={errors.notes}
      />
      <div className="flex space-x-2 mt-4">
        <Button type="submit" isLoading={loading}>{t('common.submit')}</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>
      </div>
    </form>
  );
};

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { leadSchema, LeadFormData } from '../../schemas/leadSchema';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';

interface LeadFormProps {
  initialData?: Partial<LeadFormData>;
  onSubmit: (data: LeadFormData) => Promise<void>;
  onCancel: () => void;
}

export const LeadForm: React.FC<LeadFormProps> = ({ initialData, onSubmit, onCancel }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<Partial<LeadFormData>>(initialData || {});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    try {
      const validData = leadSchema.parse(formData);
      setLoading(true);
      await onSubmit(validData);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errors' in err) {
        const zodError = err as { errors: Array<{ path: (string | number)[]; message: string }> };
        const fieldErrors: Record<string, string> = {};
        zodError.errors.forEach((error) => {
          if (error.path[0]) {
            fieldErrors[error.path[0].toString()] = error.message;
          }
        });
        setErrors(fieldErrors);
      }
    } finally {
      setLoading(false);
    }
  };

  const sourceOptions = [
    { value: 'WEBSITE', label: t('lead.sources.WEBSITE') },
    { value: 'REFERRAL', label: t('lead.sources.REFERRAL') },
    { value: 'PARTNER', label: t('lead.sources.PARTNER') },
    { value: 'OTHER', label: t('lead.sources.OTHER') },
  ];

  return (
    <form onSubmit={handleSubmit}>
      <Input
        label={t('common.name')}
        value={formData.name || ''}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        error={errors.name}
      />
      <Input
        type="email"
        label={t('common.email')}
        value={formData.email || ''}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        error={errors.email}
      />
      <Input
        label={t('common.phone')}
        value={formData.phone || ''}
        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
        error={errors.phone}
      />
      <Select
        label={t('lead.source')}
        options={sourceOptions}
        value={formData.source || ''}
        onChange={(e) => setFormData({ ...formData, source: e.target.value as 'WEBSITE' | 'REFERRAL' | 'PARTNER' | 'OTHER' })}
        error={errors.source}
      />
      <Input
        label={t('common.company')}
        value={formData.company || ''}
        onChange={(e) => setFormData({ ...formData, company: e.target.value })}
        error={errors.company}
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

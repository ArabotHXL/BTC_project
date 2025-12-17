import { z } from 'zod';

export const leadSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  source: z.enum(['WEBSITE', 'REFERRAL', 'PARTNER', 'OTHER']),
  company: z.string().optional(),
  notes: z.string().optional(),
});

export type LeadFormData = z.infer<typeof leadSchema>;

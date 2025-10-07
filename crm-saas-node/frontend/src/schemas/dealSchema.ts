import { z } from 'zod';

export const dealSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  value: z.number().min(0, 'Value must be positive'),
  stage: z.enum(['PROSPECTING', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'CLOSED_WON', 'CLOSED_LOST']),
  probability: z.number().min(0).max(100),
  expectedCloseDate: z.string().optional(),
  notes: z.string().optional(),
});

export type DealFormData = z.infer<typeof dealSchema>;

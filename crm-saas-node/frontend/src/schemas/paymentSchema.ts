import { z } from 'zod';

export const paymentSchema = z.object({
  amount: z.number().min(0.01, 'Amount must be greater than 0'),
  paymentMethod: z.enum(['CASH', 'BANK_TRANSFER', 'CREDIT_CARD', 'CHECK']),
  paymentDate: z.string().min(1, 'Payment date is required'),
  notes: z.string().optional(),
});

export type PaymentFormData = z.infer<typeof paymentSchema>;

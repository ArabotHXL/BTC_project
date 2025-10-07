import { z } from 'zod';
import { PaymentMethod, PaymentStatus } from '@prisma/client';

export const createPaymentSchema = z.object({
  invoiceId: z.string().uuid('Invalid invoice ID'),
  amount: z.number().positive('Amount must be positive'),
  method: z.nativeEnum(PaymentMethod),
  reference: z.string().optional(),
  paymentDate: z.string().datetime('Invalid date format').optional(),
});

export const updatePaymentSchema = z.object({
  amount: z.number().positive('Amount must be positive').optional(),
  method: z.nativeEnum(PaymentMethod).optional(),
  reference: z.string().optional(),
  status: z.nativeEnum(PaymentStatus).optional(),
});

export const refundPaymentSchema = z.object({
  amount: z.number().positive('Amount must be positive'),
  reason: z.string().min(1, 'Reason is required'),
});

export const rejectPaymentSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
});

export const allocatePaymentSchema = z.object({
  invoiceId: z.string().uuid('Invalid invoice ID'),
  amount: z.number().positive('Amount must be positive'),
});

export const paymentQuerySchema = z.object({
  status: z.nativeEnum(PaymentStatus).optional(),
  method: z.nativeEnum(PaymentMethod).optional(),
  invoiceId: z.string().uuid().optional(),
  accountId: z.string().uuid().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'paymentDate', 'amount']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

import { z } from 'zod';
import { InvoiceStatus, InvoiceLineItemType } from '@prisma/client';

export const lineItemSchema = z.object({
  type: z.nativeEnum(InvoiceLineItemType),
  description: z.string().min(1, 'Description is required'),
  quantity: z.number().positive('Quantity must be positive'),
  unitPrice: z.number('Unit price must be a number'),
  total: z.number('Total must be a number'),
});

export const createInvoiceSchema = z.object({
  accountId: z.string().uuid('Invalid account ID'),
  dealId: z.string().uuid('Invalid deal ID').optional(),
  contractId: z.string().uuid('Invalid contract ID').optional(),
  dueDate: z.string().datetime('Invalid date format'),
  items: z.array(lineItemSchema).min(1, 'At least one line item is required'),
  notes: z.string().optional(),
});

export const updateInvoiceSchema = z.object({
  dueDate: z.string().datetime('Invalid date format').optional(),
  status: z.nativeEnum(InvoiceStatus).optional(),
  notes: z.string().optional(),
});

export const addLineItemSchema = z.object({
  type: z.nativeEnum(InvoiceLineItemType),
  description: z.string().min(1, 'Description is required'),
  quantity: z.number().positive('Quantity must be positive'),
  unitPrice: z.number('Unit price must be a number'),
  total: z.number('Total must be a number'),
});

export const recordPaymentSchema = z.object({
  amount: z.number().positive('Amount must be positive'),
  method: z.nativeEnum(['BANK_TRANSFER', 'CREDIT_CARD', 'CRYPTO', 'CHECK', 'OTHER'] as const),
  reference: z.string().optional(),
  paidAt: z.string().datetime('Invalid date format').optional(),
});

export const voidInvoiceSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
});

export const sendInvoiceSchema = z.object({
  email: z.string().email('Invalid email format'),
});

export const invoiceQuerySchema = z.object({
  status: z.nativeEnum(InvoiceStatus).optional(),
  accountId: z.string().uuid().optional(),
  dueDateFrom: z.string().datetime().optional(),
  dueDateTo: z.string().datetime().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'dueDate', 'totalAmount', 'invoiceNumber']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

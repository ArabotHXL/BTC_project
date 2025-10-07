import { z } from 'zod';
import { BatchStatus } from '@prisma/client';

export const createBatchSchema = z.object({
  batchNumber: z.string().min(1, 'Batch number is required'),
  totalUnits: z.number().int().positive('Total units must be positive'),
  arrivalDate: z.string().datetime().optional(),
  status: z.nativeEnum(BatchStatus).optional(),
});

export const updateBatchSchema = z.object({
  batchNumber: z.string().min(1).optional(),
  totalUnits: z.number().int().positive().optional(),
  arrivalDate: z.string().datetime().optional(),
  status: z.nativeEnum(BatchStatus).optional(),
});

export const batchQuerySchema = z.object({
  status: z.nativeEnum(BatchStatus).optional(),
  arrivalDateFrom: z.string().datetime().optional(),
  arrivalDateTo: z.string().datetime().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'batchNumber', 'arrivalDate', 'status']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

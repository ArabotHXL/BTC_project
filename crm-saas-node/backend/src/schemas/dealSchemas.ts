import { z } from 'zod';
import { DealStage } from '@prisma/client';

export const createDealSchema = z.object({
  leadId: z.string().uuid().optional(),
  accountId: z.string().uuid('Invalid account ID'),
  title: z.string().min(1, 'Deal title is required'),
  value: z.number().positive('Deal value must be positive'),
  stage: z.nativeEnum(DealStage).optional(),
  probability: z.number().min(0).max(100).optional(),
  expectedClose: z.string().datetime().optional(),
});

export const updateDealSchema = z.object({
  title: z.string().min(1).optional(),
  value: z.number().positive().optional(),
  stage: z.nativeEnum(DealStage).optional(),
  probability: z.number().min(0).max(100).optional(),
  expectedClose: z.string().datetime().optional(),
});

export const updateStageSchema = z.object({
  stage: z.nativeEnum(DealStage),
  notes: z.string().optional(),
});

export const loseDealSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
  notes: z.string().optional(),
});

export const generateContractSchema = z.object({
  startDate: z.string().datetime('Invalid start date'),
  endDate: z.string().datetime('Invalid end date'),
  terms: z.string().min(1, 'Contract terms are required'),
  value: z.number().positive().optional(),
}).refine(
  (data) => new Date(data.endDate) > new Date(data.startDate),
  {
    message: 'End date must be after start date',
    path: ['endDate'],
  }
);

export const dealQuerySchema = z.object({
  stage: z.nativeEnum(DealStage).optional(),
  ownerId: z.string().uuid().optional(),
  minValue: z.number().positive().optional(),
  maxValue: z.number().positive().optional(),
  expectedCloseFrom: z.string().datetime().optional(),
  expectedCloseTo: z.string().datetime().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'value', 'expectedClose', 'stage']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

export const metricsQuerySchema = z.object({
  period: z.enum(['week', 'month', 'quarter', 'year']).default('month'),
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
});

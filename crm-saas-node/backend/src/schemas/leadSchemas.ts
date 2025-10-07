import { z } from 'zod';
import { LeadSource, LeadStatus } from '@prisma/client';

export const createLeadSchema = z.object({
  source: z.nativeEnum(LeadSource),
  company: z.string().min(1, 'Company name is required'),
  contactName: z.string().min(1, 'Contact name is required'),
  email: z.string().email('Invalid email format').optional(),
  phone: z.string().optional(),
  title: z.string().optional(),
  assignedTo: z.string().uuid().optional(),
});

export const updateLeadSchema = z.object({
  source: z.nativeEnum(LeadSource).optional(),
  company: z.string().min(1).optional(),
  contactName: z.string().min(1).optional(),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  title: z.string().optional(),
  status: z.nativeEnum(LeadStatus).optional(),
  score: z.number().min(0).max(100).optional(),
  assignedTo: z.string().uuid().optional(),
});

export const convertLeadSchema = z.object({
  dealTitle: z.string().min(1, 'Deal title is required'),
  value: z.number().positive('Deal value must be positive'),
  expectedClose: z.string().datetime('Invalid date format'),
  accountId: z.string().uuid().optional(),
  accountName: z.string().min(1).optional(),
  accountIndustry: z.string().optional(),
}).refine(
  (data) => data.accountId || data.accountName,
  {
    message: 'Either accountId or accountName must be provided',
    path: ['accountId'],
  }
);

export const bulkAssignSchema = z.object({
  leadIds: z.array(z.string().uuid()).min(1, 'At least one lead ID required'),
  userId: z.string().uuid('Invalid user ID'),
});

export const bulkUpdateStatusSchema = z.object({
  leadIds: z.array(z.string().uuid()).min(1, 'At least one lead ID required'),
  status: z.nativeEnum(LeadStatus),
});

export const disqualifyLeadSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
});

export const leadQuerySchema = z.object({
  status: z.nativeEnum(LeadStatus).optional(),
  source: z.nativeEnum(LeadSource).optional(),
  assignedTo: z.string().uuid().optional(),
  minScore: z.number().min(0).max(100).optional(),
  maxScore: z.number().min(0).max(100).optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'score', 'company', 'status']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

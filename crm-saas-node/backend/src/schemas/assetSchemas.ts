import { z } from 'zod';
import { MinerAssetStatus, MaintenanceType } from '@prisma/client';

export const createAssetSchema = z.object({
  accountId: z.string().uuid('Invalid account ID'),
  model: z.string().min(1, 'Model is required'),
  serialNumber: z.string().min(1, 'Serial number is required'),
  hashrate: z.number().positive().optional(),
  power: z.number().positive().optional(),
  location: z.string().optional(),
  purchasedAt: z.string().datetime().optional(),
});

export const updateAssetSchema = z.object({
  accountId: z.string().uuid().optional(),
  model: z.string().min(1).optional(),
  hashrate: z.number().positive().optional(),
  power: z.number().positive().optional(),
  location: z.string().optional(),
  purchasedAt: z.string().datetime().optional(),
});

export const bulkImportSchema = z.array(
  z.object({
    accountId: z.string().uuid('Invalid account ID'),
    model: z.string().min(1, 'Model is required'),
    serialNumber: z.string().min(1, 'Serial number is required'),
    hashrate: z.number().positive().optional(),
    power: z.number().positive().optional(),
    location: z.string().optional(),
    purchasedAt: z.string().datetime().optional(),
  })
).min(1).max(1000, 'Maximum 1000 assets can be imported at once');

export const updateStatusSchema = z.object({
  status: z.nativeEnum(MinerAssetStatus),
  notes: z.string().optional(),
});

export const deployAssetSchema = z.object({
  location: z.string().min(1, 'Location is required'),
  notes: z.string().optional(),
});

export const maintenanceLogSchema = z.object({
  type: z.nativeEnum(MaintenanceType),
  description: z.string().min(1, 'Description is required'),
  cost: z.number().nonnegative().optional(),
  performedBy: z.string().uuid('Invalid performer ID'),
  performedAt: z.string().datetime(),
  ticketId: z.string().uuid().optional(),
});

export const stopMiningSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
  notes: z.string().optional(),
});

export const decommissionSchema = z.object({
  reason: z.string().min(1, 'Reason is required'),
  notes: z.string().optional(),
});

export const assetQuerySchema = z.object({
  status: z.nativeEnum(MinerAssetStatus).optional(),
  model: z.string().optional(),
  accountId: z.string().uuid().optional(),
  location: z.string().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'model', 'status', 'serialNumber']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

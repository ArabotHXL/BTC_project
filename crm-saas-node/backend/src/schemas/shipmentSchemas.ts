import { z } from 'zod';
import { ShipmentStatus } from '@prisma/client';

export const createShipmentSchema = z.object({
  batchId: z.string().uuid('Invalid batch ID'),
  trackingNumber: z.string().optional(),
  carrier: z.string().optional(),
  shippedAt: z.string().datetime().optional(),
  deliveredAt: z.string().datetime().optional(),
  status: z.nativeEnum(ShipmentStatus).optional(),
});

export const updateShipmentSchema = z.object({
  trackingNumber: z.string().optional(),
  carrier: z.string().optional(),
  shippedAt: z.string().datetime().optional(),
  deliveredAt: z.string().datetime().optional(),
  status: z.nativeEnum(ShipmentStatus).optional(),
});

export const markAsShippedSchema = z.object({
  trackingNumber: z.string().min(1, 'Tracking number is required'),
});

export const shipmentQuerySchema = z.object({
  status: z.nativeEnum(ShipmentStatus).optional(),
  carrier: z.string().optional(),
  batchId: z.string().uuid().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(100).optional(),
  sortBy: z.enum(['createdAt', 'shippedAt', 'deliveredAt', 'status']).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

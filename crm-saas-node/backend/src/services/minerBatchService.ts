import { PrismaClient, MinerBatch, BatchStatus } from '@prisma/client';
import {
  CreateBatchDTO,
  UpdateBatchDTO,
  BatchSummary,
  BatchFilters,
  PaginatedResponse,
  PaginationParams,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

export class MinerBatchService {
  async getBatches(
    filters: BatchFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<MinerBatch>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: any = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.arrivalDateFrom) {
      where.arrivalDate = { ...where.arrivalDate, gte: new Date(filters.arrivalDateFrom) };
    }
    if (filters.arrivalDateTo) {
      where.arrivalDate = { ...where.arrivalDate, lte: new Date(filters.arrivalDateTo) };
    }

    const [batches, total] = await Promise.all([
      prisma.minerBatch.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          shipments: {
            select: {
              id: true,
              trackingNumber: true,
              status: true,
              carrier: true,
            },
          },
        },
      }),
      prisma.minerBatch.count({ where }),
    ]);

    return {
      data: batches,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getBatchById(id: string): Promise<MinerBatch> {
    const batch = await prisma.minerBatch.findUnique({
      where: { id },
      include: {
        shipments: true,
      },
    });

    if (!batch) {
      throw new Error('Batch not found');
    }

    return batch;
  }

  async getBatchSummary(batchId: string): Promise<BatchSummary> {
    const batch = await this.getBatchById(batchId);

    return {
      batch,
      totalUnits: batch.totalUnits,
      shipmentsCount: batch.shipments?.length || 0,
      status: batch.status,
    };
  }

  async createBatch(data: CreateBatchDTO, userId: string): Promise<MinerBatch> {
    const existing = await prisma.minerBatch.findUnique({
      where: { batchNumber: data.batchNumber },
    });

    if (existing) {
      throw new Error('Batch number already exists');
    }

    const batch = await prisma.minerBatch.create({
      data: {
        ...data,
        status: data.status || BatchStatus.ORDERED,
        arrivalDate: data.arrivalDate ? new Date(data.arrivalDate) : null,
      },
      include: {
        shipments: true,
      },
    });

    await eventPublisher.publish(EventType.BATCH_CREATED, {
      id: batch.id,
      entityType: 'BATCH',
      userId,
      ...batch,
    });

    return batch;
  }

  async updateBatch(id: string, data: UpdateBatchDTO): Promise<MinerBatch> {
    const batch = await prisma.minerBatch.update({
      where: { id },
      data: {
        ...data,
        arrivalDate: data.arrivalDate ? new Date(data.arrivalDate) : undefined,
      },
      include: {
        shipments: true,
      },
    });

    return batch;
  }

  async closeBatch(id: string): Promise<MinerBatch> {
    const batch = await prisma.minerBatch.update({
      where: { id },
      data: {
        status: BatchStatus.DEPLOYED,
      },
      include: {
        shipments: true,
      },
    });

    return batch;
  }
}

export const minerBatchService = new MinerBatchService();

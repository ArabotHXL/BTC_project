import { PrismaClient, MinerAsset, MaintenanceLog, MinerAssetStatus, MaintenanceType, ActivityType, EntityType } from '@prisma/client';
import {
  CreateAssetDTO,
  UpdateAssetDTO,
  BulkAssetDTO,
  BulkImportResult,
  InventorySummary,
  MaintenanceLogDTO,
  AssetFilters,
  PaginatedResponse,
  PaginationParams,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

export class MinerAssetService {
  private static readonly STATUS_TRANSITIONS: Record<string, string[]> = {
    'ORDERED': ['IN_TRANSIT', 'CANCELLED'],
    'IN_TRANSIT': ['RECEIVED', 'DELAYED'],
    'RECEIVED': ['DEPLOYED', 'IN_STORAGE'],
    'IN_STORAGE': ['DEPLOYED', 'DECOMMISSIONED'],
    'DEPLOYED': ['MINING', 'MAINTENANCE'],
    'MINING': ['MAINTENANCE', 'DECOMMISSIONED'],
    'MAINTENANCE': ['MINING', 'DEPLOYED', 'DECOMMISSIONED'],
    'DELAYED': ['IN_TRANSIT', 'RECEIVED'],
    'CANCELLED': [],
    'DECOMMISSIONED': [],
  };

  private validateStatusTransition(currentStatus: string, newStatus: string): void {
    const allowedTransitions = MinerAssetService.STATUS_TRANSITIONS[currentStatus];
    
    if (!allowedTransitions || !allowedTransitions.includes(newStatus)) {
      throw new Error(
        `Invalid status transition from ${currentStatus} to ${newStatus}. ` +
        `Allowed transitions: ${allowedTransitions?.join(', ') || 'none'}`
      );
    }
  }

  async getAssets(
    filters: AssetFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<MinerAsset>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: any = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.model) where.model = { contains: filters.model, mode: 'insensitive' };
    if (filters.accountId) where.accountId = filters.accountId;
    if (filters.location) where.location = { contains: filters.location, mode: 'insensitive' };

    const [assets, total] = await Promise.all([
      prisma.minerAsset.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          account: {
            select: {
              id: true,
              name: true,
              industry: true,
            },
          },
          tickets: {
            select: {
              id: true,
              subject: true,
              status: true,
              priority: true,
            },
          },
        },
      }),
      prisma.minerAsset.count({ where }),
    ]);

    return {
      data: assets,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getAssetById(id: string): Promise<MinerAsset> {
    const asset = await prisma.minerAsset.findUnique({
      where: { id },
      include: {
        account: true,
        tickets: true,
        maintenanceLogs: {
          include: {
            performer: {
              select: {
                id: true,
                name: true,
                email: true,
              },
            },
          },
          orderBy: {
            performedAt: 'desc',
          },
        },
      },
    });

    if (!asset) {
      throw new Error('Asset not found');
    }

    return asset;
  }

  async getAssetBySerialNumber(serialNumber: string): Promise<MinerAsset> {
    const asset = await prisma.minerAsset.findUnique({
      where: { serialNumber },
      include: {
        account: true,
        tickets: true,
        maintenanceLogs: {
          include: {
            performer: {
              select: {
                id: true,
                name: true,
                email: true,
              },
            },
          },
        },
      },
    });

    if (!asset) {
      throw new Error('Asset not found');
    }

    return asset;
  }

  async getAssetsByAccount(accountId: string): Promise<MinerAsset[]> {
    return await prisma.minerAsset.findMany({
      where: { accountId },
      include: {
        tickets: true,
      },
      orderBy: {
        createdAt: 'desc',
      },
    });
  }

  async getInventorySummary(accountId?: string): Promise<InventorySummary> {
    const where = accountId ? { accountId } : {};
    
    const assets = await prisma.minerAsset.findMany({
      where,
      include: { account: true },
    });

    const summary: InventorySummary = {
      total: assets.length,
      byStatus: {},
      byModel: {},
      byAccount: {},
    };

    for (const asset of assets) {
      const status = asset.status as string;
      summary.byStatus[status] = (summary.byStatus[status] || 0) + 1;
      
      summary.byModel[asset.model] = (summary.byModel[asset.model] || 0) + 1;
      
      if (asset.accountId && asset.account) {
        const accountName = asset.account.name || asset.accountId;
        summary.byAccount[accountName] = (summary.byAccount[accountName] || 0) + 1;
      }
    }

    return summary;
  }

  async createAsset(data: CreateAssetDTO, userId: string): Promise<MinerAsset> {
    const existing = await prisma.minerAsset.findUnique({
      where: { serialNumber: data.serialNumber },
    });

    if (existing) {
      throw new Error('Serial number already exists');
    }

    const asset = await prisma.minerAsset.create({
      data: {
        ...data,
        status: MinerAssetStatus.ORDERED,
        purchasedAt: data.purchasedAt ? new Date(data.purchasedAt) : null,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(asset.id, userId, `Asset created: ${asset.serialNumber}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_CREATED, {
      id: asset.id,
      entityType: 'ASSET',
      userId,
      serialNumber: asset.serialNumber,
      status: asset.status,
      ...asset,
    });

    return asset;
  }

  async updateAsset(id: string, data: UpdateAssetDTO, userId: string): Promise<MinerAsset> {
    const asset = await prisma.minerAsset.update({
      where: { id },
      data: {
        ...data,
        purchasedAt: data.purchasedAt ? new Date(data.purchasedAt) : undefined,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(id, userId, `Asset updated`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_UPDATED, {
      id: asset.id,
      serialNumber: asset.serialNumber,
      entityType: 'ASSET',
      userId,
      changes: data,
    });

    return asset;
  }

  async bulkImport(assets: BulkAssetDTO[], userId: string): Promise<BulkImportResult> {
    const results: BulkImportResult = {
      success: 0,
      failed: 0,
      errors: [],
    };

    if (assets.length > 1000) {
      throw new Error('Maximum 1000 assets can be imported at once');
    }

    for (let i = 0; i < assets.length; i++) {
      try {
        const existing = await prisma.minerAsset.findUnique({
          where: { serialNumber: assets[i].serialNumber },
        });

        if (existing) {
          results.failed++;
          results.errors.push({
            index: i,
            serialNumber: assets[i].serialNumber,
            error: 'Serial number already exists',
          });
          continue;
        }

        await prisma.minerAsset.create({
          data: {
            ...assets[i],
            status: MinerAssetStatus.ORDERED,
            purchasedAt: assets[i].purchasedAt ? new Date(assets[i].purchasedAt) : null,
          },
        });

        results.success++;
      } catch (error) {
        results.failed++;
        results.errors.push({
          index: i,
          serialNumber: assets[i].serialNumber,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    await this.createActivity('BULK_IMPORT', userId, `Bulk import: ${results.success} succeeded, ${results.failed} failed`, ActivityType.TASK);

    return results;
  }

  async updateStatus(id: string, status: MinerAssetStatus, userId: string, notes?: string): Promise<MinerAsset> {
    const existingAsset = await this.getAssetById(id);

    this.validateStatusTransition(existingAsset.status, status);

    const asset = await prisma.minerAsset.update({
      where: { id },
      data: { status },
      include: {
        account: true,
      },
    });

    const activityDesc = notes 
      ? `Asset status changed from ${existingAsset.status} to ${status}. Notes: ${notes}`
      : `Asset status changed from ${existingAsset.status} to ${status}`;

    await this.createActivity(id, userId, activityDesc, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_STATUS_CHANGED, {
      id: asset.id,
      serialNumber: asset.serialNumber,
      entityType: 'ASSET',
      userId,
      oldStatus: existingAsset.status,
      newStatus: status,
      notes,
      timestamp: new Date(),
    });

    return asset;
  }

  async deploy(id: string, location: string, userId: string): Promise<MinerAsset> {
    const existingAsset = await this.getAssetById(id);

    if (existingAsset.status !== MinerAssetStatus.RECEIVED && existingAsset.status !== MinerAssetStatus.IN_STORAGE) {
      throw new Error(
        `Cannot deploy asset in ${existingAsset.status} status. ` +
        `Asset must be in RECEIVED or IN_STORAGE status.`
      );
    }

    const asset = await prisma.minerAsset.update({
      where: { id },
      data: {
        status: MinerAssetStatus.DEPLOYED,
        location,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(id, userId, `Asset deployed to ${location}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_DEPLOYED, {
      id: asset.id,
      entityType: 'ASSET',
      userId,
      location,
      ...asset,
    });

    return asset;
  }

  async startMining(id: string, userId: string): Promise<MinerAsset> {
    const existingAsset = await this.getAssetById(id);

    if (existingAsset.status !== MinerAssetStatus.DEPLOYED && existingAsset.status !== MinerAssetStatus.MAINTENANCE) {
      throw new Error(
        `Cannot start mining for asset in ${existingAsset.status} status. ` +
        `Asset must be in DEPLOYED or MAINTENANCE status.`
      );
    }

    const asset = await prisma.minerAsset.update({
      where: { id },
      data: {
        status: MinerAssetStatus.MINING,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(id, userId, `Asset started mining`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_MINING_STARTED, {
      id: asset.id,
      entityType: 'ASSET',
      userId,
      ...asset,
    });

    return asset;
  }

  async stopMining(id: string, reason: string, userId: string): Promise<MinerAsset> {
    const existingAsset = await this.getAssetById(id);

    if (existingAsset.status !== MinerAssetStatus.MINING) {
      throw new Error(`Cannot stop mining for asset in ${existingAsset.status} status`);
    }

    const asset = await prisma.minerAsset.update({
      where: { id },
      data: {
        status: MinerAssetStatus.MAINTENANCE,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(id, userId, `Asset stopped mining. Reason: ${reason}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_MINING_STOPPED, {
      id: asset.id,
      entityType: 'ASSET',
      userId,
      reason,
      stoppedAt: new Date(),
    });

    return asset;
  }

  async decommission(id: string, reason: string, userId: string): Promise<MinerAsset> {
    const existingAsset = await this.getAssetById(id);

    const validStatuses = [MinerAssetStatus.MINING, MinerAssetStatus.MAINTENANCE, MinerAssetStatus.IN_STORAGE, MinerAssetStatus.DEPLOYED];
    if (!validStatuses.includes(existingAsset.status)) {
      throw new Error(
        `Cannot decommission asset in ${existingAsset.status} status. ` +
        `Valid statuses: ${validStatuses.join(', ')}`
      );
    }

    const asset = await prisma.minerAsset.update({
      where: { id },
      data: {
        status: MinerAssetStatus.DECOMMISSIONED,
      },
      include: {
        account: true,
      },
    });

    await this.createActivity(id, userId, `Asset decommissioned. Reason: ${reason}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.ASSET_DECOMMISSIONED, {
      id: asset.id,
      entityType: 'ASSET',
      userId,
      reason,
      decommissionedAt: new Date(),
    });

    return asset;
  }

  async createMaintenanceLog(assetId: string, data: MaintenanceLogDTO): Promise<MaintenanceLog> {
    const log = await prisma.maintenanceLog.create({
      data: {
        assetId,
        type: data.type,
        description: data.description,
        cost: data.cost || null,
        performedBy: data.performedBy,
        performedAt: new Date(data.performedAt),
        ticketId: data.ticketId || null,
      },
      include: {
        asset: true,
        performer: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
      },
    });

    await eventPublisher.publish(EventType.ASSET_MAINTENANCE, {
      id: log.id,
      assetId,
      entityType: 'MAINTENANCE_LOG',
      ...log,
    });

    return log;
  }

  async getMaintenanceHistory(assetId: string): Promise<MaintenanceLog[]> {
    return await prisma.maintenanceLog.findMany({
      where: { assetId },
      include: {
        performer: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        ticket: {
          select: {
            id: true,
            subject: true,
            status: true,
          },
        },
      },
      orderBy: {
        performedAt: 'desc',
      },
    });
  }

  private async createActivity(
    entityId: string,
    userId: string,
    description: string,
    type: ActivityType
  ): Promise<void> {
    await prisma.activity.create({
      data: {
        type,
        entityType: EntityType.ACCOUNT,
        entityId,
        userId,
        subject: description,
        description,
        completedAt: new Date(),
      },
    });
  }
}

export const minerAssetService = new MinerAssetService();

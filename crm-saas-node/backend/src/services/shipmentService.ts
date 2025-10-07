import { PrismaClient, Shipment, ShipmentStatus, MinerAssetStatus } from '@prisma/client';
import {
  CreateShipmentDTO,
  UpdateShipmentDTO,
  ShipmentFilters,
  PaginatedResponse,
  PaginationParams,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';
import { MinerAssetService } from './minerAssetService';

const prisma = new PrismaClient();

export class ShipmentService {
  private minerAssetService = new MinerAssetService();
  async getShipments(
    filters: ShipmentFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<Shipment>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: any = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.carrier) where.carrier = { contains: filters.carrier, mode: 'insensitive' };
    if (filters.batchId) where.batchId = filters.batchId;

    const [shipments, total] = await Promise.all([
      prisma.shipment.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          batch: {
            select: {
              id: true,
              batchNumber: true,
              totalUnits: true,
              status: true,
            },
          },
        },
      }),
      prisma.shipment.count({ where }),
    ]);

    return {
      data: shipments,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getShipmentById(id: string): Promise<Shipment> {
    const shipment = await prisma.shipment.findUnique({
      where: { id },
      include: {
        batch: true,
      },
    });

    if (!shipment) {
      throw new Error('Shipment not found');
    }

    return shipment;
  }

  async trackShipment(trackingNumber: string): Promise<Shipment> {
    const shipment = await prisma.shipment.findFirst({
      where: { trackingNumber },
      include: {
        batch: true,
      },
    });

    if (!shipment) {
      throw new Error('Shipment not found');
    }

    return shipment;
  }

  async createShipment(data: CreateShipmentDTO, userId: string): Promise<Shipment> {
    const shipment = await prisma.shipment.create({
      data: {
        ...data,
        status: data.status || ShipmentStatus.PENDING,
        shippedAt: data.shippedAt ? new Date(data.shippedAt) : null,
        deliveredAt: data.deliveredAt ? new Date(data.deliveredAt) : null,
      },
      include: {
        batch: true,
      },
    });

    await eventPublisher.publish(EventType.SHIPMENT_CREATED, {
      id: shipment.id,
      entityType: 'SHIPMENT',
      userId,
      ...shipment,
    });

    return shipment;
  }

  async updateShipment(id: string, data: UpdateShipmentDTO): Promise<Shipment> {
    const shipment = await prisma.shipment.update({
      where: { id },
      data: {
        ...data,
        shippedAt: data.shippedAt ? new Date(data.shippedAt) : undefined,
        deliveredAt: data.deliveredAt ? new Date(data.deliveredAt) : undefined,
      },
      include: {
        batch: true,
      },
    });

    return shipment;
  }

  async updateTrackingInfo(id: string, status: ShipmentStatus, location?: string): Promise<Shipment> {
    const shipment = await prisma.shipment.update({
      where: { id },
      data: { status },
      include: {
        batch: true,
      },
    });

    return shipment;
  }

  async markAsShipped(id: string, trackingNumber: string, userId: string): Promise<Shipment> {
    const shipment = await prisma.shipment.findUnique({
      where: { id },
      include: { assets: true },
    });

    if (!shipment) {
      throw new Error('Shipment not found');
    }

    if (shipment.status !== ShipmentStatus.PENDING) {
      throw new Error('Shipment is not in PENDING status');
    }

    const updatedShipment = await prisma.shipment.update({
      where: { id },
      data: {
        status: ShipmentStatus.SHIPPED,
        trackingNumber,
        shippedAt: new Date(),
      },
      include: {
        batch: true,
        assets: true,
      },
    });

    for (const asset of updatedShipment.assets) {
      try {
        await this.minerAssetService.updateStatus(
          asset.id,
          MinerAssetStatus.IN_TRANSIT,
          userId,
          `Shipped via ${trackingNumber}`
        );
      } catch (error) {
        console.error(`Failed to update asset ${asset.id} status:`, error instanceof Error ? error.message : 'Unknown error');
      }
    }

    await eventPublisher.publish(EventType.SHIPMENT_SHIPPED, {
      id: updatedShipment.id,
      entityType: 'SHIPMENT',
      userId,
      trackingNumber: updatedShipment.trackingNumber,
      status: updatedShipment.status,
      shippedAt: updatedShipment.shippedAt,
      assetCount: updatedShipment.assets.length,
    });

    return updatedShipment;
  }

  async markAsDelivered(id: string, userId: string): Promise<Shipment> {
    const shipment = await prisma.shipment.findUnique({
      where: { id },
      include: { assets: true },
    });

    if (!shipment) {
      throw new Error('Shipment not found');
    }

    if (shipment.status !== ShipmentStatus.SHIPPED && shipment.status !== ShipmentStatus.IN_TRANSIT) {
      throw new Error('Shipment is not in SHIPPED or IN_TRANSIT status');
    }

    const updatedShipment = await prisma.shipment.update({
      where: { id },
      data: {
        status: ShipmentStatus.DELIVERED,
        deliveredAt: new Date(),
      },
      include: {
        batch: true,
        assets: true,
      },
    });

    for (const asset of updatedShipment.assets) {
      try {
        await this.minerAssetService.updateStatus(
          asset.id,
          MinerAssetStatus.RECEIVED,
          userId,
          'Delivered'
        );
      } catch (error) {
        console.error(`Failed to update asset ${asset.id} status:`, error instanceof Error ? error.message : 'Unknown error');
      }
    }

    await eventPublisher.publish(EventType.SHIPMENT_DELIVERED, {
      id: updatedShipment.id,
      entityType: 'SHIPMENT',
      userId,
      status: updatedShipment.status,
      deliveredAt: updatedShipment.deliveredAt,
      assetCount: updatedShipment.assets.length,
    });

    return updatedShipment;
  }
}

export const shipmentService = new ShipmentService();

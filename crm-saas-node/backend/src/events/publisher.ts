import { createClient, RedisClientType } from 'redis';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export enum EventType {
  LEAD_CAPTURED = 'lead.captured',
  LEAD_CONVERTED = 'lead.converted',
  LEAD_QUALIFIED = 'lead.qualified',
  LEAD_DISQUALIFIED = 'lead.disqualified',
  DEAL_CREATED = 'deal.created',
  DEAL_STAGE_CHANGED = 'deal.stage_changed',
  DEAL_WON = 'deal.won',
  DEAL_LOST = 'deal.lost',
  CONTRACT_GENERATED = 'contract.generated',
  CONTRACT_SIGNED = 'contract.signed',
  INVOICE_CREATED = 'invoice.created',
  INVOICE_ISSUED = 'invoice.issued',
  INVOICE_PAID = 'invoice.paid',
  INVOICE_OVERDUE = 'invoice.overdue',
  PAYMENT_RECEIVED = 'payment.received',
  PAYMENT_CONFIRMED = 'payment.confirmed',
  PAYMENT_REFUNDED = 'payment.refunded',
  ASSET_CREATED = 'asset.created',
  ASSET_UPDATED = 'asset.updated',
  ASSET_STATUS_CHANGED = 'asset.status_changed',
  ASSET_DEPLOYED = 'asset.deployed',
  ASSET_MINING_STARTED = 'asset.mining_started',
  ASSET_MINING_STOPPED = 'asset.mining_stopped',
  ASSET_DECOMMISSIONED = 'asset.decommissioned',
  ASSET_MAINTENANCE = 'asset.maintenance',
  BATCH_CREATED = 'batch.created',
  SHIPMENT_CREATED = 'shipment.created',
  SHIPMENT_SHIPPED = 'shipment.shipped',
  SHIPMENT_DELIVERED = 'shipment.delivered',
  SHIPMENT_DELAYED = 'shipment.delayed',
}

export interface EventPayload {
  eventType: EventType;
  entityId: string;
  entityType: string;
  userId?: string;
  data: any;
  timestamp: Date;
}

class EventPublisher {
  private redisClient: RedisClientType | null = null;
  private isConnected: boolean = false;
  private reconnectInterval: NodeJS.Timeout | null = null;
  private reconnectDelay: number = 5000;

  async connect(): Promise<void> {
    await this.attemptConnect();
    this.startReconnectLoop();
  }

  private async attemptConnect(): Promise<void> {
    if (this.isConnected && this.redisClient) {
      return;
    }

    try {
      const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
      
      if (this.redisClient) {
        try {
          await this.redisClient.disconnect();
        } catch (err) {
        }
      }

      this.redisClient = createClient({
        url: redisUrl,
      });

      this.redisClient.on('error', (err) => {
        console.error('Redis Publisher Error:', err);
        this.isConnected = false;
      });

      this.redisClient.on('connect', () => {
        console.log('✅ Redis Publisher Connected');
        this.isConnected = true;
      });

      this.redisClient.on('disconnect', () => {
        console.log('⚠️ Redis Publisher Disconnected');
        this.isConnected = false;
      });

      await this.redisClient.connect();
      this.isConnected = true;
    } catch (error) {
      console.error('Failed to connect Redis Publisher:', error);
      this.isConnected = false;
      console.warn('⚠️  Events will be queued only. Retrying every 5 seconds...');
    }
  }

  private startReconnectLoop(): void {
    this.reconnectInterval = setInterval(async () => {
      if (!this.isConnected) {
        console.log('🔄 Attempting to reconnect Redis Publisher...');
        await this.attemptConnect();
      }
    }, this.reconnectDelay);
  }

  get connected(): boolean {
    return this.isConnected;
  }

  async publish(eventType: EventType, payload: any): Promise<void> {
    const event: EventPayload = {
      eventType,
      entityId: payload.id || payload.entityId,
      entityType: payload.entityType || this.getEntityTypeFromEvent(eventType),
      userId: payload.userId,
      data: payload,
      timestamp: new Date(),
    };

    try {
      await this.saveToEventQueue(event);

      if (this.isConnected && this.redisClient) {
        await this.redisClient.publish(
          `crm:events:${eventType}`,
          JSON.stringify(event)
        );
      }
    } catch (error) {
      console.error(`Failed to publish event ${eventType}:`, error);
    }
  }

  private async saveToEventQueue(event: EventPayload): Promise<void> {
    try {
      await prisma.eventQueue.create({
        data: {
          eventType: event.eventType,
          payloadJson: event.data,
          status: 'PENDING',
          retryCount: 0,
        },
      });
    } catch (error) {
      console.error('Failed to save event to queue:', error);
      throw error;
    }
  }

  private getEntityTypeFromEvent(eventType: EventType): string {
    if (eventType.startsWith('lead.')) return 'LEAD';
    if (eventType.startsWith('deal.')) return 'DEAL';
    if (eventType.startsWith('contract.')) return 'CONTRACT';
    if (eventType.startsWith('invoice.')) return 'INVOICE';
    if (eventType.startsWith('payment.')) return 'PAYMENT';
    if (eventType.startsWith('asset.')) return 'ASSET';
    if (eventType.startsWith('batch.')) return 'BATCH';
    if (eventType.startsWith('shipment.')) return 'SHIPMENT';
    return 'UNKNOWN';
  }

  async disconnect(): Promise<void> {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }

    if (this.redisClient && this.isConnected) {
      await this.redisClient.quit();
      this.isConnected = false;
      console.log('Redis Publisher Disconnected');
    }
  }
}

export const eventPublisher = new EventPublisher();

eventPublisher.connect().catch(console.error);

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
  INVOICE_CREATED = 'invoice.created',
  INVOICE_ISSUED = 'invoice.issued',
  INVOICE_PAID = 'invoice.paid',
  INVOICE_OVERDUE = 'invoice.overdue',
  PAYMENT_RECEIVED = 'payment.received',
  PAYMENT_CONFIRMED = 'payment.confirmed',
  PAYMENT_REFUNDED = 'payment.refunded',
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

  async connect(): Promise<void> {
    if (this.isConnected && this.redisClient) {
      return;
    }

    try {
      const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
      this.redisClient = createClient({
        url: redisUrl,
      });

      this.redisClient.on('error', (err) => {
        console.error('Redis Client Error:', err);
        this.isConnected = false;
      });

      this.redisClient.on('connect', () => {
        console.log('Redis Client Connected');
        this.isConnected = true;
      });

      await this.redisClient.connect();
    } catch (error) {
      console.error('Failed to connect to Redis:', error);
      this.isConnected = false;
    }
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
    return 'UNKNOWN';
  }

  async disconnect(): Promise<void> {
    if (this.redisClient && this.isConnected) {
      await this.redisClient.quit();
      this.isConnected = false;
    }
  }
}

export const eventPublisher = new EventPublisher();

eventPublisher.connect().catch(console.error);

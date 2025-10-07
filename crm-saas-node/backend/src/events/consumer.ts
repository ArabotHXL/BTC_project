import { PrismaClient, EventQueueStatus } from '@prisma/client';
import { HandlerRegistry } from './handlers';
import { EventPayload } from './publisher';

const prisma = new PrismaClient();

export class EventConsumer {
  private handlerRegistry: HandlerRegistry;
  private isRunning: boolean = false;
  private pollInterval: number = 5000;
  private maxRetries: number = 3;
  private pollingPromise: Promise<void> | null = null;

  constructor() {
    this.handlerRegistry = new HandlerRegistry();
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;
    console.log('🔄 Event Consumer started');

    this.pollingPromise = this.runPollingLoop().catch((error) => {
      console.error('Fatal error in polling loop:', error);
      this.isRunning = false;
    });
  }

  async stop(): Promise<void> {
    this.isRunning = false;
    
    if (this.pollingPromise) {
      await this.pollingPromise;
      this.pollingPromise = null;
    }
    
    console.log('🛑 Event Consumer stopped');
  }

  private async runPollingLoop(): Promise<void> {
    while (this.isRunning) {
      try {
        await this.processQueue();
      } catch (error) {
        console.error('Error in consumer loop:', error);
      }
      
      await this.sleep(this.pollInterval);
    }
  }

  private async processQueue(): Promise<void> {
    const pendingEvents = await prisma.eventQueue.findMany({
      where: {
        status: EventQueueStatus.PENDING,
        retryCount: {
          lt: this.maxRetries,
        },
      },
      take: 10,
      orderBy: {
        createdAt: 'asc',
      },
    });

    for (const eventRecord of pendingEvents) {
      await this.processEvent(eventRecord);
    }
  }

  private async processEvent(eventRecord: any): Promise<void> {
    try {
      await prisma.eventQueue.update({
        where: { id: eventRecord.id },
        data: { status: EventQueueStatus.PROCESSING },
      });

      const event: EventPayload = {
        eventType: eventRecord.eventType as any,
        entityId: eventRecord.payloadJson.id || eventRecord.payloadJson.entityId,
        entityType: eventRecord.payloadJson.entityType || 'UNKNOWN',
        userId: eventRecord.payloadJson.userId,
        data: eventRecord.payloadJson,
        timestamp: new Date(eventRecord.createdAt),
      };

      const handlers = this.handlerRegistry.getHandlers(eventRecord.eventType);

      for (const handler of handlers) {
        await handler.handle(event);
      }

      await prisma.eventQueue.update({
        where: { id: eventRecord.id },
        data: {
          status: EventQueueStatus.COMPLETED,
          processedAt: new Date(),
        },
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      await prisma.eventQueue.update({
        where: { id: eventRecord.id },
        data: {
          status: eventRecord.retryCount + 1 >= this.maxRetries 
            ? EventQueueStatus.FAILED 
            : EventQueueStatus.PENDING,
          retryCount: eventRecord.retryCount + 1,
          failedAt: eventRecord.retryCount + 1 >= this.maxRetries ? new Date() : null,
          errorMessage,
        },
      });

      console.error(`Failed to process event ${eventRecord.id}:`, error);
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

export const eventConsumer = new EventConsumer();

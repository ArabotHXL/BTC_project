import { createClient, RedisClientType } from 'redis';
import { HandlerRegistry } from './handlers';
import { EventPayload } from './publisher';

export class EventSubscriber {
  private redisClient: RedisClientType | null = null;
  private handlerRegistry: HandlerRegistry;
  private isConnected: boolean = false;
  private reconnectInterval: NodeJS.Timeout | null = null;
  private reconnectDelay: number = 5000;

  constructor() {
    this.handlerRegistry = new HandlerRegistry();
  }

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
        console.error('Redis Subscriber Error:', err);
        this.isConnected = false;
      });

      this.redisClient.on('connect', () => {
        console.log('✅ Redis Subscriber Connected');
        this.isConnected = true;
      });

      this.redisClient.on('disconnect', () => {
        console.log('⚠️ Redis Subscriber Disconnected');
        this.isConnected = false;
      });

      this.redisClient.on('reconnecting', () => {
        console.log('🔄 Redis Subscriber Reconnecting...');
      });

      await this.redisClient.connect();
      await this.subscribe();
      this.isConnected = true;
    } catch (error) {
      console.error('Failed to connect Redis Subscriber:', error);
      this.isConnected = false;
      console.warn('⚠️  Real-time events disabled. Retrying every 5 seconds...');
    }
  }

  private startReconnectLoop(): void {
    this.reconnectInterval = setInterval(async () => {
      if (!this.isConnected) {
        console.log('🔄 Attempting to reconnect Redis Subscriber...');
        await this.attemptConnect();
      }
    }, this.reconnectDelay);
  }

  get connected(): boolean {
    return this.isConnected;
  }

  private async subscribe(): Promise<void> {
    if (!this.redisClient || !this.isConnected) {
      throw new Error('Redis client not connected');
    }

    const eventTypes = this.handlerRegistry.getAllEventTypes();
    
    for (const eventType of eventTypes) {
      const channel = `crm:events:${eventType}`;
      await this.redisClient.subscribe(channel, async (message) => {
        await this.handleMessage(eventType, message);
      });
      console.log(`✅ Subscribed to channel: ${channel}`);
    }
  }

  private async handleMessage(eventType: string, message: string): Promise<void> {
    try {
      const event: EventPayload = JSON.parse(message);
      const handlers = this.handlerRegistry.getHandlers(eventType);

      for (const handler of handlers) {
        try {
          await handler.handle(event);
        } catch (error) {
          await handler.onError(event, error as Error);
        }
      }
    } catch (error) {
      console.error(`Failed to process message for ${eventType}:`, error);
    }
  }

  async disconnect(): Promise<void> {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }

    if (this.redisClient && this.isConnected) {
      await this.redisClient.disconnect();
      this.isConnected = false;
      console.log('📡 Redis Subscriber Disconnected');
    }
  }
}

export const eventSubscriber = new EventSubscriber();

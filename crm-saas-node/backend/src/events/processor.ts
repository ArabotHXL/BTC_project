import { eventPublisher } from './publisher';
import { eventSubscriber } from './subscriber';
import { eventConsumer } from './consumer';

export class EventProcessor {
  async start(): Promise<void> {
    console.log('🚀 Starting Event Processor...');

    const startPromises = [
      eventPublisher.connect().catch(err => {
        console.error('Publisher start failed:', err);
        return null;
      }),
      eventSubscriber.connect().catch(err => {
        console.error('Subscriber start failed:', err);
        return null;
      }),
      eventConsumer.start().catch(err => {
        console.error('Consumer start failed:', err);
        return null;
      }),
    ];

    await Promise.all(startPromises);

    console.log('✅ Event Processor started (check individual component status above)');
  }

  async stop(): Promise<void> {
    console.log('🛑 Stopping Event Processor...');

    await Promise.all([
      eventConsumer.stop().catch(err => console.error('Consumer stop error:', err)),
      eventSubscriber.disconnect().catch(err => console.error('Subscriber disconnect error:', err)),
      eventPublisher.disconnect().catch(err => console.error('Publisher disconnect error:', err)),
    ]);

    console.log('✅ Event Processor stopped');
  }

  getStatus() {
    return {
      publisher: {
        connected: eventPublisher.connected,
      },
      subscriber: {
        connected: eventSubscriber.connected,
      },
      consumer: {
        running: (eventConsumer as any).isRunning || false,
      },
    };
  }
}

export const eventProcessor = new EventProcessor();

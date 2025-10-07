import { EventPayload } from '../publisher';

export abstract class BaseEventHandler {
  abstract eventType: string;

  abstract handle(event: EventPayload): Promise<void>;

  async onError(event: EventPayload, error: Error): Promise<void> {
    console.error(`Error handling ${this.eventType}:`, {
      eventId: event.entityId,
      error: error.message,
      stack: error.stack,
    });
  }
}

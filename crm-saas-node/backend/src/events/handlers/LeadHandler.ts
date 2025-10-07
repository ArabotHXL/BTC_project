import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class LeadCapturedHandler extends BaseEventHandler {
  eventType = 'lead.captured';

  async handle(event: EventPayload): Promise<void> {
    console.log(`📋 Lead captured: ${event.entityId}`, {
      source: event.data.source,
      email: event.data.email,
    });
  }
}

export class LeadConvertedHandler extends BaseEventHandler {
  eventType = 'lead.converted';

  async handle(event: EventPayload): Promise<void> {
    console.log(`✅ Lead converted to deal: ${event.entityId}`);
  }
}

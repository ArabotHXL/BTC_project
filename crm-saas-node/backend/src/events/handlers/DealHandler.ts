import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class DealStageChangedHandler extends BaseEventHandler {
  eventType = 'deal.stage_changed';

  async handle(event: EventPayload): Promise<void> {
    console.log(`📊 Deal stage changed: ${event.entityId}`, {
      from: event.data.previousStage,
      to: event.data.newStage,
    });
  }
}

export class DealWonHandler extends BaseEventHandler {
  eventType = 'deal.won';

  async handle(event: EventPayload): Promise<void> {
    console.log(`🎉 Deal won: ${event.entityId}`, {
      value: event.data.totalValue,
    });
  }
}

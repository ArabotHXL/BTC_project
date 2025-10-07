import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class ContractGeneratedHandler extends BaseEventHandler {
  eventType = 'contract.generated';

  async handle(event: EventPayload): Promise<void> {
    console.log(`📄 Contract generated: ${event.data.contractNumber || event.entityId}`, {
      dealId: event.data.dealId,
      accountId: event.data.accountId,
    });
  }
}

export class ContractSignedHandler extends BaseEventHandler {
  eventType = 'contract.signed';

  async handle(event: EventPayload): Promise<void> {
    console.log(`✍️ Contract signed: ${event.data.contractNumber || event.entityId}`, {
      dealId: event.data.dealId,
      accountId: event.data.accountId,
    });
  }
}

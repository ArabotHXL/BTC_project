import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class PaymentReceivedHandler extends BaseEventHandler {
  eventType = 'payment.received';

  async handle(event: EventPayload): Promise<void> {
    console.log(`💵 Payment received: ${event.entityId}`, {
      amount: event.data.amount,
      invoiceId: event.data.invoiceId,
    });
  }
}

export class PaymentConfirmedHandler extends BaseEventHandler {
  eventType = 'payment.confirmed';

  async handle(event: EventPayload): Promise<void> {
    console.log(`✅ Payment confirmed: ${event.entityId}`, {
      amount: event.data.amount,
      status: event.data.status,
    });
  }
}

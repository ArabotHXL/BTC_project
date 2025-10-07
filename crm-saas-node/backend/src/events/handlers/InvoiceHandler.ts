import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class InvoiceCreatedHandler extends BaseEventHandler {
  eventType = 'invoice.created';

  async handle(event: EventPayload): Promise<void> {
    console.log(`🧾 Invoice created: ${event.data.invoiceNumber}`);
  }
}

export class InvoiceIssuedHandler extends BaseEventHandler {
  eventType = 'invoice.issued';

  async handle(event: EventPayload): Promise<void> {
    console.log(`📮 Invoice issued: ${event.data.invoiceNumber}`, {
      accountId: event.data.accountId,
      amount: event.data.totalAmount,
    });
  }
}

export class InvoicePaidHandler extends BaseEventHandler {
  eventType = 'invoice.paid';

  async handle(event: EventPayload): Promise<void> {
    console.log(`💰 Invoice paid: ${event.data.invoiceNumber}`);
  }
}

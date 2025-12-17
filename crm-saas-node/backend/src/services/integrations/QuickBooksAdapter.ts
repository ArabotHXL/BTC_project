import crypto from 'crypto';
import { IntegrationAdapter, WebhookEvent, WebhookEventType } from './types';
import { prisma } from '../../db';

export class QuickBooksAdapter implements IntegrationAdapter {
  name = 'QuickBooks';

  isConfigured(): boolean {
    return !!process.env.QUICKBOOKS_CLIENT_ID && !!process.env.QUICKBOOKS_CLIENT_SECRET;
  }

  validateWebhookSignature(payload: string, signature: string, secret: string): boolean {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payload);
    const expected = hmac.digest('base64');
    return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  }

  async handleWebhook(event: any): Promise<void> {
    console.log(`[QuickBooks] Webhook received:`, event);

    const webhookEvent: WebhookEvent = {
      type: this.mapEventType(event.eventType),
      source: 'quickbooks',
      timestamp: new Date().toISOString(),
      data: event,
    };

    await prisma.webhookLog.create({
      data: {
        source: 'quickbooks',
        eventType: webhookEvent.type,
        payload: event,
        processedAt: new Date(),
      },
    });
  }

  private mapEventType(qbEventType: string): WebhookEventType {
    const mapping: Record<string, WebhookEventType> = {
      'INVOICE.CREATED': WebhookEventType.INVOICE_CREATED,
      'INVOICE.PAID': WebhookEventType.INVOICE_PAID,
    };
    return mapping[qbEventType] || WebhookEventType.INVOICE_CREATED;
  }
}

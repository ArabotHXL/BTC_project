import crypto from 'crypto';
import { IntegrationAdapter, WebhookEvent, WebhookEventType } from './types';
import { prisma } from '../../db';

export class DocuSignAdapter implements IntegrationAdapter {
  name = 'DocuSign';

  isConfigured(): boolean {
    return !!process.env.DOCUSIGN_INTEGRATION_KEY && !!process.env.DOCUSIGN_SECRET;
  }

  validateWebhookSignature(payload: string, signature: string, secret: string): boolean {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payload);
    const expected = hmac.digest('hex');
    return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  }

  async handleWebhook(event: any): Promise<void> {
    console.log(`[DocuSign] Webhook received:`, event);

    const webhookEvent: WebhookEvent = {
      type: this.mapEventType(event.event),
      source: 'docusign',
      timestamp: new Date().toISOString(),
      data: event,
    };

    await prisma.webhookLog.create({
      data: {
        source: 'docusign',
        eventType: webhookEvent.type,
        payload: event,
        processedAt: new Date(),
      },
    });
  }

  private mapEventType(dsEventType: string): WebhookEventType {
    const mapping: Record<string, WebhookEventType> = {
      'envelope-completed': WebhookEventType.DOCUMENT_SIGNED,
      'envelope-sent': WebhookEventType.DOCUMENT_SENT,
    };
    return mapping[dsEventType] || WebhookEventType.DOCUMENT_SENT;
  }
}

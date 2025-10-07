import { IntegrationAdapter, WebhookEvent, WebhookEventType } from './types';
import { prisma } from '../../db';

export class GmailAdapter implements IntegrationAdapter {
  name = 'Gmail';

  isConfigured(): boolean {
    return !!process.env.GMAIL_CLIENT_ID && !!process.env.GMAIL_CLIENT_SECRET;
  }

  validateWebhookSignature(payload: string, signature: string, secret: string): boolean {
    if (!signature) {
      console.warn('[Gmail] Missing Pub/Sub token');
      return false;
    }

    const tokenMatch = signature.match(/^Bearer\s+(.+)$/i);
    if (!tokenMatch) {
      console.warn('[Gmail] Invalid Pub/Sub token format');
      return false;
    }

    const token = tokenMatch[1];

    if (token !== secret) {
      console.warn('[Gmail] Pub/Sub token mismatch');
      return false;
    }

    return true;
  }

  async handleWebhook(event: any): Promise<void> {
    console.log(`[Gmail] Webhook received:`, event);

    const webhookEvent: WebhookEvent = {
      type: WebhookEventType.EMAIL_RECEIVED,
      source: 'gmail',
      timestamp: new Date().toISOString(),
      data: event,
    };

    await prisma.webhookLog.create({
      data: {
        source: 'gmail',
        eventType: webhookEvent.type,
        payload: event,
        processedAt: new Date(),
      },
    });
  }

  private mapEventType(gmailEventType: string): WebhookEventType {
    return WebhookEventType.EMAIL_RECEIVED;
  }
}

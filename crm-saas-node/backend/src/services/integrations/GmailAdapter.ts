import { IntegrationAdapter, WebhookEvent, WebhookEventType } from './types';
import { prisma } from '../../db';
import * as crypto from 'crypto';

export class GmailAdapter implements IntegrationAdapter {
  name = 'Gmail';

  isConfigured(): boolean {
    return !!process.env.GMAIL_CLIENT_ID && !!process.env.GMAIL_CLIENT_SECRET;
  }

  validateWebhookSignature(payload: string, signature: string, secret: string): boolean {
    // Gmail使用Google Pub/Sub，验证通过HMAC-SHA256（payload + secret）
    // 注：这是占位实现，生产环境应使用Google JWT验证
    if (!secret) {
      console.warn('[Gmail] No webhook secret configured');
      return false;
    }
    
    // HMAC-SHA256验证：签名 = HMAC(payload, secret)
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payload);
    const expectedSignature = hmac.digest('hex');
    
    // 长度检查（防止timingSafeEqual抛异常）
    const signatureBuffer = Buffer.from(signature);
    const expectedBuffer = Buffer.from(expectedSignature);
    
    if (signatureBuffer.length !== expectedBuffer.length) {
      return false;
    }
    
    return crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
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

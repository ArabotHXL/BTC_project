/**
 * 通用集成适配器接口
 */
export interface IntegrationAdapter {
  name: string;
  isConfigured(): boolean;
  validateWebhookSignature(payload: string, signature: string, secret: string): boolean;
  handleWebhook(event: any): Promise<void>;
}

/**
 * Webhook事件类型
 */
export enum WebhookEventType {
  INVOICE_CREATED = 'invoice.created',
  INVOICE_PAID = 'invoice.paid',
  DOCUMENT_SIGNED = 'document.signed',
  DOCUMENT_SENT = 'document.sent',
  EMAIL_SENT = 'email.sent',
  EMAIL_RECEIVED = 'email.received',
}

/**
 * Webhook事件
 */
export interface WebhookEvent {
  type: WebhookEventType;
  source: string;
  timestamp: string;
  data: any;
}

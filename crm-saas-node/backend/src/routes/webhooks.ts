import { Router, Request, Response } from 'express';
import { QuickBooksAdapter } from '../services/integrations/QuickBooksAdapter';
import { DocuSignAdapter } from '../services/integrations/DocuSignAdapter';
import { GmailAdapter } from '../services/integrations/GmailAdapter';

const router = Router();

const adapters = {
  quickbooks: new QuickBooksAdapter(),
  docusign: new DocuSignAdapter(),
  gmail: new GmailAdapter(),
};

/**
 * POST /webhooks/intake
 * 通用webhook接收端点
 */
router.post('/intake', async (req: Request, res: Response) => {
  try {
    const source = req.query.source as string;
    const signature = req.headers['x-webhook-signature'] as string;
    const payload = JSON.stringify(req.body);

    if (!source || !adapters[source as keyof typeof adapters]) {
      return res.status(400).json({ error: 'Invalid or missing source parameter' });
    }

    // 强制要求签名header
    if (!signature) {
      return res.status(401).json({ error: 'Missing X-Webhook-Signature header' });
    }

    const adapter = adapters[source as keyof typeof adapters];

    // 签名验证（必须通过）
    const secret = process.env[`${source.toUpperCase()}_WEBHOOK_SECRET`] || '';
    if (!adapter.validateWebhookSignature(payload, signature, secret)) {
      return res.status(401).json({ error: 'Invalid webhook signature' });
    }

    // 处理webhook
    await adapter.handleWebhook(req.body);

    return res.status(200).json({ success: true, message: 'Webhook processed' });
  } catch (error: any) {
    console.error('Webhook processing error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /webhooks/health
 * 健康检查端点
 */
router.get('/health', (req: Request, res: Response) => {
  const status = Object.entries(adapters).map(([name, adapter]) => ({
    name: adapter.name,
    configured: adapter.isConfigured(),
  }));

  res.json({ adapters: status });
});

export default router;

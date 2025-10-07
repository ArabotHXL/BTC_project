import request from 'supertest';
import crypto from 'crypto';
import { app } from '../../server';

describe('POST /api/webhooks/intake', () => {
  beforeEach(() => {
    delete process.env.QUICKBOOKS_WEBHOOK_SECRET;
    delete process.env.GMAIL_WEBHOOK_SECRET;
    delete process.env.DOCUSIGN_WEBHOOK_SECRET;
  });

  it('should reject request without signature', async () => {
    process.env.QUICKBOOKS_WEBHOOK_SECRET = 'test_secret';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=quickbooks')
      .send({ eventType: 'INVOICE.CREATED' });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Missing webhook signature');
  });

  it('should reject request with invalid signature', async () => {
    process.env.QUICKBOOKS_WEBHOOK_SECRET = 'test_secret';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=quickbooks')
      .set('X-Webhook-Signature', 'invalid_signature')
      .send({ eventType: 'INVOICE.CREATED' });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Invalid webhook signature');
  });

  it('should accept request with valid signature', async () => {
    process.env.QUICKBOOKS_WEBHOOK_SECRET = 'test_secret';
    
    const payload = JSON.stringify({ eventType: 'INVOICE.CREATED' });
    const hmac = crypto.createHmac('sha256', 'test_secret');
    hmac.update(payload);
    const signature = hmac.digest('base64');
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=quickbooks')
      .set('X-Webhook-Signature', signature)
      .send({ eventType: 'INVOICE.CREATED' });
    
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
  });

  it('should reject Gmail request without Authorization header', async () => {
    process.env.GMAIL_WEBHOOK_SECRET = 'gmail_token';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=gmail')
      .send({ message: { data: 'base64data' } });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Missing webhook signature');
  });

  it('should accept Gmail request with valid token', async () => {
    process.env.GMAIL_WEBHOOK_SECRET = 'gmail_token';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=gmail')
      .set('Authorization', 'Bearer gmail_token')
      .send({ message: { data: 'base64data' } });
    
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
  });

  it('should return 500 when secret is not configured', async () => {
    const res = await request(app)
      .post('/api/webhooks/intake?source=quickbooks')
      .set('X-Webhook-Signature', 'some_signature')
      .send({ eventType: 'INVOICE.CREATED' });
    
    expect(res.status).toBe(500);
    expect(res.body.error).toContain('Integration not properly configured');
  });

  it('should reject DocuSign request with invalid signature', async () => {
    process.env.DOCUSIGN_WEBHOOK_SECRET = 'docusign_secret';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=docusign')
      .set('X-Webhook-Signature', 'invalid_signature')
      .send({ event: 'envelope-completed' });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Invalid webhook signature');
  });

  it('should accept DocuSign request with valid signature', async () => {
    process.env.DOCUSIGN_WEBHOOK_SECRET = 'docusign_secret';
    
    const payload = JSON.stringify({ event: 'envelope-completed' });
    const hmac = crypto.createHmac('sha256', 'docusign_secret');
    hmac.update(payload);
    const signature = hmac.digest('hex');
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=docusign')
      .set('X-Webhook-Signature', signature)
      .send({ event: 'envelope-completed' });
    
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
  });

  it('should reject Gmail request with invalid token format', async () => {
    process.env.GMAIL_WEBHOOK_SECRET = 'gmail_token';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=gmail')
      .set('Authorization', 'InvalidFormat gmail_token')
      .send({ message: { data: 'base64data' } });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Invalid webhook signature');
  });

  it('should reject Gmail request with mismatched token', async () => {
    process.env.GMAIL_WEBHOOK_SECRET = 'correct_token';
    
    const res = await request(app)
      .post('/api/webhooks/intake?source=gmail')
      .set('Authorization', 'Bearer wrong_token')
      .send({ message: { data: 'base64data' } });
    
    expect(res.status).toBe(401);
    expect(res.body.error).toContain('Invalid webhook signature');
  });
});

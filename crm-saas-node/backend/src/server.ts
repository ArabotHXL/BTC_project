import 'dotenv/config';
import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { setupSwagger } from './swagger';
import authRoutes from './routes/auth';
import leadRoutes from './routes/leads';
import dealRoutes from './routes/deals';
import invoiceRoutes from './routes/invoices';
import paymentRoutes from './routes/payments';
import assetRoutes from './routes/assets';
import batchRoutes from './routes/batches';
import shipmentRoutes from './routes/shipments';
import healthRoutes from './routes/health';
import webhookRoutes from './routes/webhooks';
import { eventPublisher } from './events/publisher';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/api', (_req: Request, res: Response) => {
  res.json({
    message: 'Welcome to CRM Platform API',
    version: '1.0.0',
  });
});

app.use('/api', healthRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/leads', leadRoutes);
app.use('/api/deals', dealRoutes);
app.use('/api/invoices', invoiceRoutes);
app.use('/api/payments', paymentRoutes);
app.use('/api/assets', assetRoutes);
app.use('/api/batches', batchRoutes);
app.use('/api/shipments', shipmentRoutes);
app.use('/api/webhooks', webhookRoutes);

if (process.env.ENABLE_API_DOCS !== 'false') {
  setupSwagger(app);
}

if (require.main === module) {
  app.listen(PORT, async () => {
    console.log(`🚀 Server is running on http://localhost:${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
    if (process.env.ENABLE_API_DOCS !== 'false') {
      console.log(`📚 API Docs: http://localhost:${PORT}/api-docs`);
    }
    console.log(`🔐 Auth endpoints: http://localhost:${PORT}/api/auth`);
    console.log(`📋 Lead endpoints: http://localhost:${PORT}/api/leads`);
    console.log(`💼 Deal endpoints: http://localhost:${PORT}/api/deals`);
    console.log(`🧾 Invoice endpoints: http://localhost:${PORT}/api/invoices`);
    console.log(`💰 Payment endpoints: http://localhost:${PORT}/api/payments`);
    console.log(`🏗️  Asset endpoints: http://localhost:${PORT}/api/assets`);
    console.log(`📦 Batch endpoints: http://localhost:${PORT}/api/batches`);
    console.log(`🚚 Shipment endpoints: http://localhost:${PORT}/api/shipments`);
    console.log(`🔗 Webhook endpoints: http://localhost:${PORT}/api/webhooks`);
    
    await eventPublisher.connect();
    console.log(`✅ Event Publisher initialized`);
  });
}

export { app };

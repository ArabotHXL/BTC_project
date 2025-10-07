import 'dotenv/config';
import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import authRoutes from './routes/auth';
import leadRoutes from './routes/leads';
import dealRoutes from './routes/deals';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/api/health', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'CRM Backend API',
  });
});

app.get('/api', (_req: Request, res: Response) => {
  res.json({
    message: 'Welcome to CRM Platform API',
    version: '1.0.0',
  });
});

app.use('/api/auth', authRoutes);
app.use('/api/leads', leadRoutes);
app.use('/api/deals', dealRoutes);

app.listen(PORT, () => {
  console.log(`🚀 Server is running on http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`🔐 Auth endpoints: http://localhost:${PORT}/api/auth`);
  console.log(`📋 Lead endpoints: http://localhost:${PORT}/api/leads`);
  console.log(`💼 Deal endpoints: http://localhost:${PORT}/api/deals`);
});

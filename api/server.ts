/**
 * TypeScript API Server - Microservices layer for HashInsight Enterprise
 * Provides: DataHub, Miner Control, Curtailment Strategy APIs
 */

import express from 'express';
import cors from 'cors';
import * as dotenv from 'dotenv';
import { dataHub } from './datahub';
import { minerRegistry } from '../modules/miner_adapters/registry';
import { curtailmentService } from '../modules/curtailment_service';
import { eventLogger } from '../common/eventLogger';
import { requireAuth, requireConfirmation } from './auth';

dotenv.config();

const app = express();
const PORT = parseInt(process.env.TS_API_PORT || '3000');

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'hashinsight-typescript-services',
    timestamp: new Date().toISOString()
  });
});

// DataHub APIs
app.get('/api/datahub/price', async (req, res) => {
  try {
    const result = await dataHub.getPrice();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.get('/api/datahub/chain', async (req, res) => {
  try {
    const result = await dataHub.getChainData();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.get('/api/datahub/all', async (req, res) => {
  try {
    const result = await dataHub.getAll();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

// Miner Control APIs (require authentication)
app.get('/api/miners', requireAuth, async (req, res) => {
  try {
    const adapters = minerRegistry.getAllAdapters();
    const states = await Promise.all(
      Array.from(adapters.values()).map(adapter => adapter.getState())
    );
    res.json({ miners: states });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.get('/api/miners/:id', requireAuth, async (req, res) => {
  try {
    const miners = minerRegistry.loadMiners();
    const config = miners.find(m => m.id === req.params.id);
    
    if (!config) {
      return res.status(404).json({ error: 'Miner not found' });
    }

    const adapter = minerRegistry.getAdapter(config);
    const state = await adapter.getState();
    res.json(state);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.post('/api/miners/:id/power-limit', requireAuth, requireConfirmation, async (req, res) => {
  try {
    const { percent, actor } = req.body;

    const miners = minerRegistry.loadMiners();
    const config = miners.find(m => m.id === req.params.id);
    
    if (!config) {
      return res.status(404).json({ error: 'Miner not found' });
    }

    const adapter = minerRegistry.getAdapter(config);
    await adapter.setPowerLimit(percent);

    eventLogger.recordCommand(req.params.id, 'setPowerLimit', actor || 'api', 'ok', { percent });
    res.json({ success: true, miner_id: req.params.id, power_limit: percent });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.post('/api/miners/:id/reboot', requireAuth, requireConfirmation, async (req, res) => {
  try {
    const { actor } = req.body;

    const miners = minerRegistry.loadMiners();
    const config = miners.find(m => m.id === req.params.id);
    
    if (!config) {
      return res.status(404).json({ error: 'Miner not found' });
    }

    const adapter = minerRegistry.getAdapter(config);
    await adapter.reboot();

    eventLogger.recordCommand(req.params.id, 'reboot', actor || 'api', 'ok');
    res.json({ success: true, miner_id: req.params.id });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

// Curtailment Strategy APIs (require authentication)
app.post('/api/curtailment/plan', requireAuth, async (req, res) => {
  try {
    const { electricity_price, btc_price, target_savings } = req.body;

    // Get current miner states
    const adapters = minerRegistry.getAllAdapters();
    const miners = await Promise.all(
      Array.from(adapters.values()).map(adapter => adapter.getState())
    );

    const plan = await curtailmentService.calculatePlan(
      electricity_price,
      miners,
      btc_price,
      target_savings
    );

    res.json(plan);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.post('/api/curtailment/execute', requireAuth, requireConfirmation, async (req, res) => {
  try {
    const { plan_id, plan, confirmed, actor } = req.body;

    await curtailmentService.executePlan(plan, confirmed, actor || 'api');
    res.json({ success: true, plan_id });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

app.post('/api/curtailment/rollback', requireAuth, async (req, res) => {
  try {
    const { plan_id, actor } = req.body;

    await curtailmentService.rollbackPlan(plan_id, actor || 'api');
    res.json({ success: true, plan_id });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

// Events Export API (require authentication for sensitive data)
app.get('/api/events/export', requireAuth, async (req, res) => {
  try {
    const { since, format } = req.query;
    
    // For now, export today's events
    const today = new Date().toISOString().split('T')[0];
    const events = eventLogger.readEvents(today);

    if (format === 'csv') {
      const csv = eventLogger.exportToCSV(events);
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="events_${today}.csv"`);
      res.send(csv);
    } else {
      res.json({ events });
    }
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 HashInsight TypeScript Services running on port ${PORT}`);
  console.log(`   DataHub API: http://localhost:${PORT}/api/datahub/*`);
  console.log(`   Miner Control: http://localhost:${PORT}/api/miners`);
  console.log(`   Curtailment: http://localhost:${PORT}/api/curtailment/*`);
  console.log(`   Events: http://localhost:${PORT}/api/events/export`);
  console.log(`   Demo Mode: ${process.env.DEMO_MODE === '1' ? 'ENABLED' : 'DISABLED'}`);
});

export default app;

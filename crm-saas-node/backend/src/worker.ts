import { eventProcessor } from './events/processor';
import { eventPublisher } from './events/publisher';
import { eventSubscriber } from './events/subscriber';
import express from 'express';

let isShuttingDown = false;
let isReady = false;

async function startWorker() {
  console.log('🔧 Event Worker Starting...');

  const app = express();
  const healthPort = process.env.WORKER_HEALTH_PORT ? parseInt(process.env.WORKER_HEALTH_PORT) : 3001;

  app.get('/health', (req, res) => {
    const healthStatus = {
      status: isReady && !isShuttingDown ? 'healthy' : 'unhealthy',
      uptime: process.uptime(),
      ready: isReady,
      shuttingDown: isShuttingDown,
      components: {
        publisher: eventPublisher.connected,
        subscriber: eventSubscriber.connected,
      },
      timestamp: new Date().toISOString(),
    };

    const statusCode = healthStatus.status === 'healthy' ? 200 : 503;
    res.status(statusCode).json(healthStatus);
  });

  app.listen(healthPort, () => {
    console.log(`📊 Worker health endpoint: http://localhost:${healthPort}/health`);
  });

  const shutdown = async (signal: string) => {
    if (isShuttingDown) {
      return;
    }
    isShuttingDown = true;
    
    console.log(`Received ${signal}, shutting down gracefully...`);
    try {
      await eventProcessor.stop();
      console.log('✅ Worker shutdown complete');
      process.exit(0);
    } catch (error) {
      console.error('Error during shutdown:', error);
      process.exit(1);
    }
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  let retries = 0;
  const maxRetries = 5;
  const retryDelay = 5000;

  while (retries < maxRetries) {
    try {
      await eventProcessor.start();
      isReady = true;
      console.log('✅ Event Worker ready');
      return;
    } catch (error) {
      retries++;
      console.error(`Failed to start event processor (attempt ${retries}/${maxRetries}):`, error);
      
      if (retries >= maxRetries) {
        console.error('Max retries reached. Worker cannot start.');
        process.exit(1);
      }
      
      console.log(`Retrying in ${retryDelay/1000} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
}

startWorker().catch((error) => {
  console.error('Fatal error in worker:', error);
  process.exit(1);
});

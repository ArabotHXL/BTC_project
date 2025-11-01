/**
 * Mempool.space Chain Data Provider (Fallback)
 */

import axios from 'axios';
import { ChainData } from '../../../common/types';
import { eventLogger } from '../../../common/eventLogger';

export async function fetchChainData(): Promise<ChainData> {
  const startTime = Date.now();
  const url = `${process.env.MEMPOOL_API_URL || 'https://mempool.space/api'}/v1/mining/hashrate/3d`;
  const difficultyUrl = `${process.env.MEMPOOL_API_URL || 'https://mempool.space/api'}/v1/difficulty-adjustment`;

  try {
    const [hashrateResponse, difficultyResponse] = await Promise.all([
      axios.get(url, { timeout: 8000 }),
      axios.get(difficultyUrl, { timeout: 8000 })
    ]);

    const networkHashrate = hashrateResponse.data.currentHashrate / 1e18; // Convert to EH/s
    const difficulty = difficultyResponse.data.difficulty;

    const latency = Date.now() - startTime;
    const data: ChainData = {
      difficulty,
      block_reward: 3.125,
      network_hashrate: networkHashrate,
      timestamp: Date.now(),
      source: 'mempool'
    };

    eventLogger.recordDataFetch('mempool', 'chain_data', 'ok', latency, {
      difficulty,
      hashrate: networkHashrate
    });
    return data;
  } catch (error) {
    const latency = Date.now() - startTime;
    eventLogger.recordDataFetch('mempool', 'chain_data', 'error', latency, { error: String(error) });
    throw error;
  }
}

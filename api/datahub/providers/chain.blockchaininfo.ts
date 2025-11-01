/**
 * Blockchain.info Chain Data Provider (Primary)
 */

import axios from 'axios';
import { ChainData } from '../../../common/types';
import { eventLogger } from '../../../common/eventLogger';

export async function fetchChainData(): Promise<ChainData> {
  const startTime = Date.now();
  const url = `${process.env.BLOCKCHAIN_INFO_API_URL || 'https://blockchain.info'}/q/getdifficulty`;
  const hashrateUrl = `${process.env.BLOCKCHAIN_INFO_API_URL || 'https://blockchain.info'}/q/hashrate`;

  try {
    const [diffResponse, hashrateResponse] = await Promise.all([
      axios.get(url, { timeout: 8000 }),
      axios.get(hashrateUrl, { timeout: 8000 })
    ]);

    const difficulty = parseFloat(diffResponse.data);
    const networkHashrate = parseFloat(hashrateResponse.data) / 1e18; // Convert to EH/s

    const latency = Date.now() - startTime;
    const data: ChainData = {
      difficulty,
      block_reward: 3.125, // Current Bitcoin block reward
      network_hashrate: networkHashrate,
      timestamp: Date.now(),
      source: 'blockchain_info'
    };

    eventLogger.recordDataFetch('blockchain_info', 'chain_data', 'ok', latency, {
      difficulty,
      hashrate: networkHashrate
    });
    return data;
  } catch (error) {
    const latency = Date.now() - startTime;
    eventLogger.recordDataFetch('blockchain_info', 'chain_data', 'error', latency, { error: String(error) });
    throw error;
  }
}

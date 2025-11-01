/**
 * CoinGecko Price Provider (Primary)
 */

import axios from 'axios';
import { PriceData } from '../../../common/types';
import { eventLogger } from '../../../common/eventLogger';

export async function fetchPrice(): Promise<PriceData> {
  const startTime = Date.now();
  const url = `${process.env.COINGECKO_API_URL || 'https://api.coingecko.com/api/v3'}/simple/price?ids=bitcoin&vs_currencies=usd`;

  try {
    const response = await axios.get(url, { timeout: 8000 });
    const btcPrice = response.data.bitcoin.usd;

    const latency = Date.now() - startTime;
    const data: PriceData = {
      btc_usd: btcPrice,
      timestamp: Date.now(),
      source: 'coingecko'
    };

    eventLogger.recordDataFetch('coingecko', 'btc_price_usd', 'ok', latency, { price: btcPrice });
    return data;
  } catch (error) {
    const latency = Date.now() - startTime;
    eventLogger.recordDataFetch('coingecko', 'btc_price_usd', 'error', latency, { error: String(error) });
    throw error;
  }
}

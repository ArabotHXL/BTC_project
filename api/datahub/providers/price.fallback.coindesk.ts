/**
 * CoinDesk Price Provider (Fallback)
 */

import axios from 'axios';
import { PriceData } from '../../../common/types';
import { eventLogger } from '../../../common/eventLogger';

export async function fetchPrice(): Promise<PriceData> {
  const startTime = Date.now();
  const url = `${process.env.COINDESK_API_URL || 'https://api.coindesk.com/v1'}/bpi/currentprice/BTC.json`;

  try {
    const response = await axios.get(url, { timeout: 8000 });
    const btcPrice = response.data.bpi.USD.rate_float;

    const latency = Date.now() - startTime;
    const data: PriceData = {
      btc_usd: btcPrice,
      timestamp: Date.now(),
      source: 'coindesk'
    };

    eventLogger.recordDataFetch('coindesk', 'btc_price_usd', 'ok', latency, { price: btcPrice });
    return data;
  } catch (error) {
    const latency = Date.now() - startTime;
    eventLogger.recordDataFetch('coindesk', 'btc_price_usd', 'error', latency, { error: String(error) });
    throw error;
  }
}

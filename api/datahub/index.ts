/**
 * DataHub - Unified real-time data facade with intelligent fallback
 */

import { PriceData, ChainData, DataHubResponse } from '../../common/types';
import { cacheManager } from '../../common/cache';
import { retryWithBackoff } from '../../common/retry';
import * as coingecko from './providers/price.coingecko';
import * as coindesk from './providers/price.fallback.coindesk';
import * as blockchainInfo from './providers/chain.blockchaininfo';
import * as mempool from './providers/chain.fallback.mempool';

const PRICE_TTL = parseInt(process.env.DATAHUB_PRICE_TTL || '30');
const CHAIN_TTL = parseInt(process.env.DATAHUB_CHAIN_TTL || '300');
const TIMEOUT_MS = parseInt(process.env.DATAHUB_TIMEOUT_MS || '8000');

export class DataHub {
  /**
   * Get BTC price with intelligent fallback
   */
  async getPrice(): Promise<DataHubResponse<PriceData>> {
    const cacheKey = 'price:btc_usd';
    const cached = cacheManager.get<PriceData>(cacheKey);

    if (cached) {
      return {
        data: cached,
        cached: true,
        source: cached.source,
        refreshed_at: new Date(cached.timestamp).toISOString()
      };
    }

    // Try primary source (CoinGecko)
    try {
      const data = await retryWithBackoff(() => coingecko.fetchPrice(), {
        maxAttempts: 2,
        timeout: TIMEOUT_MS
      });
      cacheManager.set(cacheKey, data, PRICE_TTL);
      return {
        data,
        cached: false,
        source: data.source,
        refreshed_at: new Date().toISOString()
      };
    } catch (primaryError) {
      console.warn('CoinGecko failed, trying fallback...', primaryError);

      // Try fallback source (CoinDesk)
      try {
        const data = await retryWithBackoff(() => coindesk.fetchPrice(), {
          maxAttempts: 2,
          timeout: TIMEOUT_MS
        });
        cacheManager.set(cacheKey, data, PRICE_TTL);
        return {
          data,
          cached: false,
          source: data.source,
          refreshed_at: new Date().toISOString()
        };
      } catch (fallbackError) {
        // Both sources failed
        throw new Error(`All price sources failed: ${primaryError}, ${fallbackError}`);
      }
    }
  }

  /**
   * Get chain data (difficulty, hashrate, block reward) with intelligent fallback
   */
  async getChainData(): Promise<DataHubResponse<ChainData>> {
    const cacheKey = 'chain:bitcoin';
    const cached = cacheManager.get<ChainData>(cacheKey);

    if (cached) {
      return {
        data: cached,
        cached: true,
        source: cached.source,
        refreshed_at: new Date(cached.timestamp).toISOString()
      };
    }

    // Try primary source (Blockchain.info)
    try {
      const data = await retryWithBackoff(() => blockchainInfo.fetchChainData(), {
        maxAttempts: 2,
        timeout: TIMEOUT_MS
      });
      cacheManager.set(cacheKey, data, CHAIN_TTL);
      return {
        data,
        cached: false,
        source: data.source,
        refreshed_at: new Date().toISOString()
      };
    } catch (primaryError) {
      console.warn('Blockchain.info failed, trying fallback...', primaryError);

      // Try fallback source (Mempool.space)
      try {
        const data = await retryWithBackoff(() => mempool.fetchChainData(), {
          maxAttempts: 2,
          timeout: TIMEOUT_MS
        });
        cacheManager.set(cacheKey, data, CHAIN_TTL);
        return {
          data,
          cached: false,
          source: data.source,
          refreshed_at: new Date().toISOString()
        };
      } catch (fallbackError) {
        throw new Error(`All chain data sources failed: ${primaryError}, ${fallbackError}`);
      }
    }
  }

  /**
   * Get all data (price + chain) in one call
   */
  async getAll(): Promise<{
    price: DataHubResponse<PriceData>;
    chain: DataHubResponse<ChainData>;
  }> {
    const [price, chain] = await Promise.all([
      this.getPrice(),
      this.getChainData()
    ]);

    return { price, chain };
  }
}

export const dataHub = new DataHub();

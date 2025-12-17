/**
 * DataHub Fallback Test - Verify fallback logic when primary source errors
 */

import { DataHub } from '../api/datahub';
import * as blockchainInfo from '../api/datahub/providers/chain.blockchaininfo';
import * as mempool from '../api/datahub/providers/chain.fallback.mempool';

jest.mock('../api/datahub/providers/chain.blockchaininfo');
jest.mock('../api/datahub/providers/chain.fallback.mempool');

describe('DataHub Fallback Mechanism', () => {
  let dataHub: DataHub;

  beforeEach(() => {
    dataHub = new DataHub();
    jest.clearAllMocks();
  });

  it('should fallback to mempool when blockchain.info fails', async () => {
    // Mock primary to fail
    (blockchainInfo.fetchChainData as jest.Mock).mockRejectedValue(new Error('API Error'));

    // Mock fallback to succeed
    (mempool.fetchChainData as jest.Mock).mockResolvedValue({
      difficulty: 50000000000000,
      block_reward: 3.125,
      network_hashrate: 500,
      timestamp: Date.now(),
      source: 'mempool'
    });

    const result = await dataHub.getChainData();

    expect(result.data.source).toBe('mempool');
    expect(result.data.difficulty).toBe(50000000000000);
    expect(mempool.fetchChainData).toHaveBeenCalled();
  });
});

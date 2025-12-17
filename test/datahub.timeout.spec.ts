/**
 * DataHub Timeout Test - Verify fallback mechanism when primary source times out
 */

import { DataHub } from '../api/datahub';
import * as coingecko from '../api/datahub/providers/price.coingecko';
import * as coindesk from '../api/datahub/providers/price.fallback.coindesk';

jest.mock('../api/datahub/providers/price.coingecko');
jest.mock('../api/datahub/providers/price.fallback.coindesk');

describe('DataHub Timeout Handling', () => {
  let dataHub: DataHub;

  beforeEach(() => {
    dataHub = new DataHub();
    jest.clearAllMocks();
  });

  it('should use fallback when primary source times out', async () => {
    // Mock primary source to timeout
    (coingecko.fetchPrice as jest.Mock).mockRejectedValue(new Error('Request timeout'));

    // Mock fallback source to succeed
    (coindesk.fetchPrice as jest.Mock).mockResolvedValue({
      btc_usd: 45000,
      timestamp: Date.now(),
      source: 'coindesk'
    });

    const result = await dataHub.getPrice();

    expect(result.data.source).toBe('coindesk');
    expect(result.data.btc_usd).toBe(45000);
    expect(coindesk.fetchPrice).toHaveBeenCalled();
  });

  it('should throw error when all sources fail', async () => {
    (coingecko.fetchPrice as jest.Mock).mockRejectedValue(new Error('Timeout'));
    (coindesk.fetchPrice as jest.Mock).mockRejectedValue(new Error('Timeout'));

    await expect(dataHub.getPrice()).rejects.toThrow('All price sources failed');
  });
});

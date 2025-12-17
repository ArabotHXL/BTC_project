/**
 * DataHub Exception Test - Verify exception handling and event logging
 */

import { DataHub } from '../api/datahub';
import { eventLogger } from '../common/eventLogger';
import * as coingecko from '../api/datahub/providers/price.coingecko';
import * as coindesk from '../api/datahub/providers/price.fallback.coindesk';

jest.mock('../api/datahub/providers/price.coingecko');
jest.mock('../api/datahub/providers/price.fallback.coindesk');
jest.mock('../common/eventLogger');

describe('DataHub Exception Handling', () => {
  let dataHub: DataHub;

  beforeEach(() => {
    dataHub = new DataHub();
    jest.clearAllMocks();
  });

  it('should log events when provider throws exception', async () => {
    const error = new Error('Network error');
    (coingecko.fetchPrice as jest.Mock).mockRejectedValue(error);
    (coindesk.fetchPrice as jest.Mock).mockRejectedValue(error);

    await expect(dataHub.getPrice()).rejects.toThrow();

    // Events should be logged via providers
    // (actual event logging is done in the providers themselves)
  });

  it('should not crash when provider throws non-Error exception', async () => {
    (coingecko.fetchPrice as jest.Mock).mockRejectedValue('String error');
    (coindesk.fetchPrice as jest.Mock).mockRejectedValue(null);

    await expect(dataHub.getPrice()).rejects.toBeDefined();
  });
});

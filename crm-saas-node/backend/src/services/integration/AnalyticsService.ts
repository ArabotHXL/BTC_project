import { FlaskClient } from './FlaskClient';

export class AnalyticsService {
  private flaskClient: FlaskClient;

  constructor() {
    this.flaskClient = new FlaskClient();
  }

  async getBtcPrice() {
    const response = await this.flaskClient.get('/api/get_btc_price');
    return response.success ? response.data : null;
  }

  async getNetworkStats() {
    const response = await this.flaskClient.get('/api/network-stats');
    return response.success ? response.data : null;
  }

  async getNetworkHistory(params?: { days?: number }) {
    const response = await this.flaskClient.get('/api/network-history', params);
    return response.success ? response.data : null;
  }

  async getTechnicalIndicators() {
    const response = await this.flaskClient.get('/api/analytics/technical-indicators');
    return response.success ? response.data : null;
  }

  async getTreasuryOverview() {
    const response = await this.flaskClient.get('/api/treasury/overview');
    return response.success ? response.data : null;
  }

  async getTradingSignals() {
    const response = await this.flaskClient.get('/api/treasury/signals');
    return response.success ? response.data : null;
  }

  async runBacktest(strategyParams: any) {
    const response = await this.flaskClient.post('/api/treasury/backtest', strategyParams);
    return response.success ? response.data : null;
  }
}

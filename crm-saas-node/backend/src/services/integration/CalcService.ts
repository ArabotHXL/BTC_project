import { FlaskClient } from './FlaskClient';

interface CalculationInput {
  miner_model: string;
  quantity: number;
  electricity_cost: number;
  hashrate_decay?: number;
  curtailment?: number;
  bitcoin_price?: number;
  network_difficulty?: number;
  pool_fee?: number;
}

interface CalculationResult {
  daily_revenue: number;
  daily_power_cost: number;
  daily_net_profit: number;
  monthly_net_profit: number;
  annual_net_profit: number;
  roi_days: number;
  payback_period: string;
  btc_per_day: number;
  power_consumption_kw: number;
}

export class CalcService {
  private flaskClient: FlaskClient;

  constructor() {
    this.flaskClient = new FlaskClient();
  }

  /**
   * 执行挖矿计算（使用生产endpoint）
   */
  async calculate(input: CalculationInput): Promise<CalculationResult | null> {
    const response = await this.flaskClient.post('/calculate', input);

    if (response.success && response.data) {
      return response.data;
    }

    console.error('Calculation failed:', response.error);
    return null;
  }

  /**
   * 获取矿机数据
   */
  async getMinersData() {
    const response = await this.flaskClient.get('/api/get_miners_data');

    if (response.success && response.data) {
      return response.data;
    }

    return null;
  }

  /**
   * 获取SHA256挖矿对比数据
   */
  async getSha256Comparison() {
    const response = await this.flaskClient.get('/api/sha256_mining_comparison');

    if (response.success && response.data) {
      return response.data;
    }

    return null;
  }
}

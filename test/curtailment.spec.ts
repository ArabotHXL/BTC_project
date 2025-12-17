/**
 * Curtailment Service Tests - Verify plan calculation and aggregation
 */

import { CurtailmentService } from '../modules/curtailment_service';
import { MinerState } from '../common/types';

describe('Curtailment Service', () => {
  let service: CurtailmentService;

  beforeEach(() => {
    service = new CurtailmentService();
  });

  it('should calculate correct revenue impact with negative values', async () => {
    const miners: MinerState[] = [
      {
        id: 'miner-001',
        model: 'Antminer S19 Pro',
        ip: '192.168.1.101',
        online: true,
        hashrate_5m: 110, // TH/s
        temp_c: 65,
        fan_rpm: [5000, 5100],
        power_w: 3250,
        last_seen: new Date().toISOString()
      },
      {
        id: 'miner-002',
        model: 'Antminer S19j Pro',
        ip: '192.168.1.102',
        online: true,
        hashrate_5m: 90, // TH/s
        temp_c: 70,
        fan_rpm: [4800, 4900],
        power_w: 3050,
        last_seen: new Date().toISOString()
      }
    ];

    // High electricity price to trigger curtailment
    const electricityPrice = 0.15; // USD/kWh
    const btcPrice = 30000; // Low BTC price

    const plan = await service.calculatePlan(electricityPrice, miners, btcPrice);

    // Revenue impact should be negative (loss)
    expect(plan.expected_revenue_impact_usd).toBeLessThan(0);
    
    // Savings should be positive
    expect(plan.expected_savings_usd).toBeGreaterThan(0);

    // Each action's revenue_impact_usd should be negative
    plan.actions.forEach(action => {
      expect(action.revenue_impact_usd).toBeLessThan(0);
    });
  });

  it('should calculate impact_pct based on total revenue, not power', async () => {
    const miners: MinerState[] = [
      {
        id: 'miner-001',
        model: 'Test Miner',
        ip: '192.168.1.101',
        online: true,
        hashrate_5m: 100,
        temp_c: 60,
        fan_rpm: [5000],
        power_w: 3000,
        last_seen: new Date().toISOString()
      }
    ];

    const plan = await service.calculatePlan(0.20, miners, 25000); // Very high price

    // impact_pct should be percentage of revenue, not power
    // Range should be reasonable (0-100%)
    expect(plan.impact_pct).toBeGreaterThanOrEqual(0);
    expect(plan.impact_pct).toBeLessThanOrEqual(100);

    // Calculate expected: abs(revenue_impact) / total_revenue * 100
    const totalRevenue = miners.reduce((sum, m) => {
      const btcPerHour = (m.hashrate_5m * 1e12 / 146e15) * 6.25;
      return sum + (btcPerHour * 25000);
    }, 0);

    const expectedImpactPct = (Math.abs(plan.expected_revenue_impact_usd) / totalRevenue) * 100;
    expect(plan.impact_pct).toBeCloseTo(expectedImpactPct, 1);
  });

  it('should prioritize curtailing least profitable miners first', async () => {
    const miners: MinerState[] = [
      {
        id: 'profitable',
        model: 'High Efficiency',
        ip: '192.168.1.101',
        online: true,
        hashrate_5m: 150, // High hashrate
        temp_c: 60,
        fan_rpm: [5000],
        power_w: 2500, // Low power
        last_seen: new Date().toISOString()
      },
      {
        id: 'unprofitable',
        model: 'Low Efficiency',
        ip: '192.168.1.102',
        online: true,
        hashrate_5m: 50, // Low hashrate
        temp_c: 70,
        fan_rpm: [4500],
        power_w: 4000, // High power
        last_seen: new Date().toISOString()
      }
    ];

    const plan = await service.calculatePlan(0.15, miners, 30000);

    // Unprofitable miner should be curtailed first
    if (plan.actions.length > 0) {
      expect(plan.actions[0].miner_id).toBe('unprofitable');
    }
  });

  it('should aggregate totals correctly across multiple actions', async () => {
    const miners: MinerState[] = [
      { id: 'm1', model: 'Test', ip: '1.1.1.1', online: true, hashrate_5m: 100, temp_c: 60, fan_rpm: [5000], power_w: 3000, last_seen: '' },
      { id: 'm2', model: 'Test', ip: '1.1.1.2', online: true, hashrate_5m: 95, temp_c: 62, fan_rpm: [4900], power_w: 2900, last_seen: '' },
      { id: 'm3', model: 'Test', ip: '1.1.1.3', online: true, hashrate_5m: 90, temp_c: 65, fan_rpm: [4800], power_w: 2800, last_seen: '' }
    ];

    const plan = await service.calculatePlan(0.18, miners, 28000);

    // Manually sum action values
    const manualSavings = plan.actions.reduce((sum, a) => sum + a.savings_usd, 0);
    const manualRevenueImpact = plan.actions.reduce((sum, a) => sum + a.revenue_impact_usd, 0);

    expect(plan.expected_savings_usd).toBeCloseTo(manualSavings, 2);
    expect(plan.expected_revenue_impact_usd).toBeCloseTo(manualRevenueImpact, 2);
  });
});

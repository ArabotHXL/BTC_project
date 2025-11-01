/**
 * Curtailment Service - Calculates optimal power throttling/stopping strategy
 * based on electricity prices to minimize revenue loss
 */

import * as fs from 'fs';
import { eventLogger } from '../../common/eventLogger';
import { CurtailmentPlan, CurtailmentAction, CurtailmentConfig, MinerState } from '../../common/types';
import { v4 as uuidv4 } from 'uuid';

export class CurtailmentService {
  private config: CurtailmentConfig;

  constructor(configPath: string = './config/curtailment.json') {
    this.config = this.loadConfig(configPath);
  }

  /**
   * Calculate curtailment plan based on current electricity price
   */
  async calculatePlan(
    electricityPrice: number, // USD per kWh
    miners: MinerState[],
    btcPrice: number,
    targetSavings?: number // Optional: target savings in USD/hour
  ): Promise<CurtailmentPlan> {
    const startTime = Date.now();

    // Calculate profitability for each miner
    const minerProfitability = miners.map(miner => {
      const powerKw = miner.power_w / 1000;
      const electricityCost = powerKw * electricityPrice; // USD/hour
      const btcPerHour = (miner.hashrate_5m * 1e12 / 146e15) * 6.25; // Simplified
      const revenue = btcPerHour * btcPrice; // USD/hour
      const profit = revenue - electricityCost;

      return {
        miner,
        electricityCost,
        revenue,
        profit,
        profitMargin: profit / revenue
      };
    });

    // Sort by profit margin (lowest first - these get curtailed first)
    minerProfitability.sort((a, b) => a.profitMargin - b.profitMargin);

    const actions: CurtailmentAction[] = [];
    let totalSavings = 0;
    let totalRevenueImpact = 0;

    // Strategy: Stop unprofitable miners, throttle marginal ones
    for (const item of minerProfitability) {
      if (item.profit < 0) {
        // Miner is unprofitable - stop it
        const action: CurtailmentAction = {
          miner_id: item.miner.id,
          action: 'stop',
          current_power_w: item.miner.power_w,
          target_power_w: 0,
          savings_usd: item.electricityCost,
          revenue_impact_usd: -item.revenue
        };
        actions.push(action);
        totalSavings += item.electricityCost;
        totalRevenueImpact += action.revenue_impact_usd; // Use negative value from action
      } else if (item.profitMargin < 0.2 && item.profit < (targetSavings || Infinity)) {
        // Low margin - throttle to max_throttle
        const throttlePercent = this.config.max_throttle;
        const newPower = item.miner.power_w * throttlePercent;
        const powerSavings = item.miner.power_w - newPower;
        const savingsUsd = (powerSavings / 1000) * electricityPrice;
        const revenueImpact = item.revenue * (1 - throttlePercent);

        const action: CurtailmentAction = {
          miner_id: item.miner.id,
          action: 'throttle',
          current_power_w: item.miner.power_w,
          target_power_w: newPower,
          savings_usd: savingsUsd,
          revenue_impact_usd: -revenueImpact
        };
        actions.push(action);
        totalSavings += savingsUsd;
        totalRevenueImpact += action.revenue_impact_usd; // Use negative value from action
      }

      // Stop if we've reached target savings
      if (targetSavings && totalSavings >= targetSavings) {
        break;
      }
    }

    // Calculate total revenue for impact percentage
    const totalRevenue = minerProfitability.reduce((sum, item) => sum + item.revenue, 0);
    
    const plan: CurtailmentPlan = {
      id: uuidv4(),
      created_at: new Date().toISOString(),
      electricity_price: electricityPrice,
      actions,
      expected_savings_usd: totalSavings,
      expected_revenue_impact_usd: totalRevenueImpact,
      impact_pct: totalRevenue > 0 ? (Math.abs(totalRevenueImpact) / totalRevenue) * 100 : 0
    };

    const latency = Date.now() - startTime;
    eventLogger.appendEvent({
      type: 'curtailment.plan',
      source: 'system',
      key: plan.id,
      status: 'ok',
      latency_ms: latency,
      details: {
        electricity_price: electricityPrice,
        actions_count: actions.length,
        savings_usd: totalSavings,
        revenue_impact_usd: totalRevenueImpact
      }
    });

    return plan;
  }

  /**
   * Execute a curtailment plan (requires confirmation)
   */
  async executePlan(
    plan: CurtailmentPlan,
    confirmed: boolean,
    actor: string
  ): Promise<void> {
    if (!confirmed && this.config.require_confirm) {
      throw new Error('Curtailment execution requires confirmation');
    }

    const startTime = Date.now();

    try {
      // In production, this would call minerAdapter.setPowerLimit() or stop()
      // For now, just log the execution
      if (process.env.DEMO_MODE === '1') {
        console.log(`[DEMO] Executing curtailment plan ${plan.id} with ${plan.actions.length} actions`);
      } else {
        // TODO: Call actual miner adapters
        console.log(`Executing curtailment plan ${plan.id}`);
      }

      const latency = Date.now() - startTime;
      eventLogger.appendEvent({
        type: 'curtailment.execute',
        source: 'ui',
        key: plan.id,
        status: 'ok',
        latency_ms: latency,
        actor,
        details: {
          actions_count: plan.actions.length,
          confirmed,
          demo_mode: process.env.DEMO_MODE === '1'
        }
      });
    } catch (error) {
      const latency = Date.now() - startTime;
      eventLogger.appendEvent({
        type: 'curtailment.execute',
        source: 'ui',
        key: plan.id,
        status: 'error',
        latency_ms: latency,
        actor,
        details: { error: String(error) }
      });
      throw error;
    }
  }

  /**
   * Rollback a curtailment plan (restore full power)
   */
  async rollbackPlan(planId: string, actor: string): Promise<void> {
    const startTime = Date.now();

    try {
      // In production, restore all miners to full power
      if (process.env.DEMO_MODE === '1') {
        console.log(`[DEMO] Rolling back curtailment plan ${planId}`);
      } else {
        console.log(`Rolling back curtailment plan ${planId}`);
      }

      const latency = Date.now() - startTime;
      eventLogger.appendEvent({
        type: 'curtailment.rollback',
        source: 'ui',
        key: planId,
        status: 'ok',
        latency_ms: latency,
        actor
      });
    } catch (error) {
      const latency = Date.now() - startTime;
      eventLogger.appendEvent({
        type: 'curtailment.rollback',
        source: 'ui',
        key: planId,
        status: 'error',
        latency_ms: latency,
        actor,
        details: { error: String(error) }
      });
      throw error;
    }
  }

  private loadConfig(configPath: string): CurtailmentConfig {
    if (!fs.existsSync(configPath)) {
      // Default config
      return {
        price_threshold: parseFloat(process.env.CURTAILMENT_PRICE_THRESHOLD || '0.10'),
        max_throttle: parseFloat(process.env.CURTAILMENT_MAX_THROTTLE || '0.5'),
        require_confirm: process.env.CURTAILMENT_REQUIRE_CONFIRM !== 'false'
      };
    }

    const content = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(content);
  }
}

export const curtailmentService = new CurtailmentService();

/**
 * WhatsMiner Simulator - Simulates WhatsMiner M50/M53/M56 series for demo purposes
 */

import { MinerAdapter, MinerState, MinerConfig } from '../../common/types';
import { eventLogger } from '../../common/eventLogger';

export class WhatsMinerSimulator implements MinerAdapter {
  private config: MinerConfig;
  private currentPowerLimit: number = 1.0;
  private isOnline: boolean = true;
  private baseHashrate: number = 120; // TH/s for M50s

  constructor(config: MinerConfig) {
    this.config = config;
    // Set base hashrate based on model
    if (config.model.includes('M53')) {
      this.baseHashrate = 226;
    } else if (config.model.includes('M56')) {
      this.baseHashrate = 230;
    }
  }

  async getState(): Promise<MinerState> {
    const startTime = Date.now();
    
    // Simulate network latency
    await this.sleep(50 + Math.random() * 100);

    try {
      // Simulate realistic variations
      const hashrateVariation = 0.95 + Math.random() * 0.1; // ±5%
      const tempVariation = 60 + Math.random() * 15; // 60-75°C
      const fanBase = 4500 + Math.random() * 500;

      const state: MinerState = {
        id: this.config.id,
        model: this.config.model,
        ip: this.config.ip,
        online: this.isOnline,
        hashrate_5m: this.baseHashrate * this.currentPowerLimit * hashrateVariation,
        temp_c: tempVariation,
        fan_rpm: [
          Math.round(fanBase),
          Math.round(fanBase + 100),
          Math.round(fanBase - 50),
          Math.round(fanBase + 150)
        ],
        power_w: Math.round(3360 * this.currentPowerLimit), // M50s ~3360W
        last_seen: new Date().toISOString()
      };

      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'getState',
        'system',
        'ok',
        { latency_ms: latency, simulated: true }
      );

      return state;
    } catch (error) {
      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'getState',
        'system',
        'error',
        { latency_ms: latency, error: String(error) }
      );
      throw error;
    }
  }

  async setPowerLimit(percent: number): Promise<void> {
    if (percent < 0 || percent > 1) {
      throw new Error('Power limit must be between 0 and 1');
    }

    const startTime = Date.now();
    await this.sleep(100); // Simulate command processing

    this.currentPowerLimit = percent;

    const latency = Date.now() - startTime;
    eventLogger.recordCommand(
      this.config.id,
      'setPowerLimit',
      'system',
      'ok',
      { latency_ms: latency, power_limit: percent, simulated: true }
    );
  }

  async reboot(): Promise<void> {
    const startTime = Date.now();
    await this.sleep(200);

    // Simulate offline period
    this.isOnline = false;
    setTimeout(() => {
      this.isOnline = true;
    }, 30000); // 30 seconds offline

    const latency = Date.now() - startTime;
    eventLogger.recordCommand(
      this.config.id,
      'reboot',
      'system',
      'ok',
      { latency_ms: latency, simulated: true }
    );
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

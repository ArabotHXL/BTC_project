/**
 * Antminer Adapter - Controls Antminer S19/S21 series via CGMiner/BMminer API
 * Supports HTTP/TCP connections to CGMiner RPC interface
 */

import * as net from 'net';
import { MinerAdapter, MinerState, MinerConfig } from '../../common/types';
import { eventLogger } from '../../common/eventLogger';

export class AntminerAdapter implements MinerAdapter {
  private config: MinerConfig;
  private timeout: number;

  constructor(config: MinerConfig) {
    this.config = config;
    this.timeout = parseInt(process.env.ANTMINER_TIMEOUT_MS || '5000');
  }

  /**
   * Get current miner state via CGMiner API
   */
  async getState(): Promise<MinerState> {
    const startTime = Date.now();
    try {
      // CGMiner API commands: summary, stats, pools
      const [summary, stats] = await Promise.all([
        this.sendCommand({ command: 'summary' }),
        this.sendCommand({ command: 'stats' })
      ]);

      const latency = Date.now() - startTime;

      // Parse response
      const summaryData = summary.SUMMARY?.[0] || {};
      const statsData = stats.STATS?.[0] || {};

      const state: MinerState = {
        id: this.config.id,
        model: this.config.model,
        ip: this.config.ip,
        online: true,
        hashrate_5m: this.parseHashrate(summaryData['MHS 5m'] || summaryData['GHS 5m']),
        temp_c: this.parseTemperature(statsData),
        fan_rpm: this.parseFanSpeeds(statsData),
        power_w: statsData.power || 0,
        last_seen: new Date().toISOString()
      };

      eventLogger.recordCommand(
        this.config.id,
        'getState',
        'system',
        'ok',
        { latency_ms: latency, hashrate: state.hashrate_5m }
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

      // Return offline state
      return {
        id: this.config.id,
        model: this.config.model,
        ip: this.config.ip,
        online: false,
        hashrate_5m: 0,
        temp_c: 0,
        fan_rpm: [],
        power_w: 0,
        last_seen: new Date().toISOString()
      };
    }
  }

  /**
   * Set power limit (requires advanced firmware)
   */
  async setPowerLimit(percent: number): Promise<void> {
    if (percent < 0 || percent > 1) {
      throw new Error('Power limit must be between 0 and 1');
    }

    const startTime = Date.now();
    try {
      // Note: This requires custom firmware (e.g., Vnish, Braiins OS+)
      // Stock firmware doesn't support power limiting via API
      const command = {
        command: 'setpowerlimit',
        parameter: Math.round(percent * 100)
      };

      await this.sendCommand(command);

      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'setPowerLimit',
        'system',
        'ok',
        { latency_ms: latency, power_limit: percent }
      );
    } catch (error) {
      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'setPowerLimit',
        'system',
        'error',
        { latency_ms: latency, error: String(error) }
      );
      throw error;
    }
  }

  /**
   * Reboot miner
   */
  async reboot(): Promise<void> {
    const startTime = Date.now();
    try {
      await this.sendCommand({ command: 'restart' });

      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'reboot',
        'system',
        'ok',
        { latency_ms: latency }
      );
    } catch (error) {
      const latency = Date.now() - startTime;
      eventLogger.recordCommand(
        this.config.id,
        'reboot',
        'system',
        'error',
        { latency_ms: latency, error: String(error) }
      );
      throw error;
    }
  }

  /**
   * Send TCP command to CGMiner API
   */
  private sendCommand(command: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const socket = new net.Socket();
      let responseData = '';

      const timer = setTimeout(() => {
        socket.destroy();
        reject(new Error('Connection timeout'));
      }, this.timeout);

      socket.connect(this.config.port, this.config.ip, () => {
        const cmd = JSON.stringify(command);
        socket.write(cmd);
      });

      socket.on('data', (data) => {
        responseData += data.toString();
      });

      socket.on('end', () => {
        clearTimeout(timer);
        try {
          // CGMiner returns JSON with null byte at the end
          const cleaned = responseData.replace(/\0/g, '');
          const parsed = JSON.parse(cleaned);
          resolve(parsed);
        } catch (error) {
          reject(new Error(`Failed to parse response: ${error}`));
        }
      });

      socket.on('error', (error) => {
        clearTimeout(timer);
        reject(error);
      });
    });
  }

  private parseHashrate(value: any): number {
    if (!value) return 0;
    // Convert MH/s to TH/s
    return parseFloat(value) / 1000000;
  }

  private parseTemperature(stats: any): number {
    // Try common temperature fields
    const temp = stats.temp1 || stats.temp2 || stats.temp3 || stats.temp || 0;
    return parseFloat(temp);
  }

  private parseFanSpeeds(stats: any): number[] {
    const fans: number[] = [];
    for (let i = 1; i <= 4; i++) {
      const fanKey = `fan${i}`;
      if (stats[fanKey]) {
        fans.push(parseFloat(stats[fanKey]));
      }
    }
    return fans;
  }
}

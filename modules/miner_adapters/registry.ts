/**
 * Miner Adapter Registry - Resolves correct adapter based on miner configuration
 */

import * as fs from 'fs';
import * as path from 'path';
import { MinerAdapter, MinerConfig } from '../../common/types';
import { AntminerAdapter } from './antminer';
import { WhatsMinerSimulator } from './whatsminer.sim';

export class MinerAdapterRegistry {
  private configPath: string;
  private adapters: Map<string, MinerAdapter> = new Map();

  constructor(configPath: string = './config/miners.json') {
    this.configPath = configPath;
  }

  /**
   * Load miners from configuration file
   */
  loadMiners(): MinerConfig[] {
    if (!fs.existsSync(this.configPath)) {
      console.warn(`Miner config not found: ${this.configPath}, using demo mode`);
      return this.getDefaultDemoMiners();
    }

    const content = fs.readFileSync(this.configPath, 'utf8');
    const config = JSON.parse(content);
    return config.miners || [];
  }

  /**
   * Get adapter for a specific miner
   */
  getAdapter(config: MinerConfig): MinerAdapter {
    // Check cache
    if (this.adapters.has(config.id)) {
      return this.adapters.get(config.id)!;
    }

    // Create new adapter based on type
    let adapter: MinerAdapter;

    if (process.env.DEMO_MODE === '1' || config.adapter_type === 'simulator') {
      adapter = new WhatsMinerSimulator(config);
    } else if (config.adapter_type === 'antminer') {
      adapter = new AntminerAdapter(config);
    } else if (config.adapter_type === 'whatsminer') {
      // When real WhatsMiner adapter is implemented, use it here
      adapter = new WhatsMinerSimulator(config);
    } else {
      throw new Error(`Unknown adapter type: ${config.adapter_type}`);
    }

    // Cache it
    this.adapters.set(config.id, adapter);
    return adapter;
  }

  /**
   * Get all configured miners
   */
  getAllAdapters(): Map<string, MinerAdapter> {
    const miners = this.loadMiners();
    miners.forEach(config => {
      if (!this.adapters.has(config.id)) {
        this.getAdapter(config);
      }
    });
    return this.adapters;
  }

  /**
   * Default demo miners for testing
   */
  private getDefaultDemoMiners(): MinerConfig[] {
    return [
      {
        id: 'demo-antminer-s19-001',
        model: 'Antminer S19 Pro',
        ip: '192.168.1.101',
        port: 4028,
        adapter_type: 'simulator'
      },
      {
        id: 'demo-antminer-s19-002',
        model: 'Antminer S19j Pro',
        ip: '192.168.1.102',
        port: 4028,
        adapter_type: 'simulator'
      },
      {
        id: 'demo-whatsminer-m50s-001',
        model: 'WhatsMiner M50S',
        ip: '192.168.1.103',
        port: 4028,
        adapter_type: 'simulator'
      },
      {
        id: 'demo-whatsminer-m53s-001',
        model: 'WhatsMiner M53S+',
        ip: '192.168.1.104',
        port: 4028,
        adapter_type: 'simulator'
      },
      {
        id: 'demo-whatsminer-m56s-001',
        model: 'WhatsMiner M56S++',
        ip: '192.168.1.105',
        port: 4028,
        adapter_type: 'simulator'
      }
    ];
  }
}

// Export singleton
export const minerRegistry = new MinerAdapterRegistry();

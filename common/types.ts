/**
 * Common TypeScript types for HashInsight Enterprise
 */

// Event Logging Types
export interface Event {
  ts: string; // ISO 8601 timestamp with Z
  type: EventType;
  source: EventSource;
  key: string;
  status: EventStatus;
  latency_ms?: number;
  details?: Record<string, any>;
  actor?: string; // "system" or "user:<email>"
}

export type EventType =
  | 'datahub.fetch'
  | 'monitor.alert'
  | 'monitor.ack'
  | 'monitor.command'
  | 'curtailment.plan'
  | 'curtailment.execute'
  | 'curtailment.rollback'
  | 'batch.etl'
  | 'report.daily'
  | 'email.sent';

export type EventSource =
  | 'coingecko'
  | 'coindesk'
  | 'blockchain_info'
  | 'mempool'
  | 'antminer'
  | 'whatsminer'
  | 'simulator'
  | 'ui'
  | 'system';

export type EventStatus = 'ok' | 'timeout' | 'error' | 'triggered' | 'acknowledged';

// Miner Adapter Types
export interface MinerState {
  id: string;
  model: string;
  ip: string;
  online: boolean;
  hashrate_5m: number; // TH/s
  temp_c: number;
  fan_rpm: number[];
  power_w: number;
  last_seen: string; // ISO 8601
}

export interface MinerAdapter {
  getState(): Promise<MinerState>;
  setPowerLimit(percent: number): Promise<void>;
  reboot(): Promise<void>;
}

export interface MinerConfig {
  id: string;
  model: string;
  ip: string;
  port: number;
  username?: string;
  password?: string;
  adapter_type: 'antminer' | 'whatsminer' | 'simulator';
}

// DataHub Types
export interface PriceData {
  btc_usd: number;
  timestamp: number;
  source: string;
}

export interface ChainData {
  difficulty: number;
  block_reward: number;
  network_hashrate: number; // EH/s
  timestamp: number;
  source: string;
}

export interface DataHubResponse<T> {
  data: T;
  cached: boolean;
  source: string;
  refreshed_at: string;
}

// Curtailment Strategy Types
export interface CurtailmentPlan {
  id: string;
  created_at: string;
  electricity_price: number;
  actions: CurtailmentAction[];
  expected_savings_usd: number;
  expected_revenue_impact_usd: number;
  impact_pct: number;
}

export interface CurtailmentAction {
  miner_id: string;
  action: 'throttle' | 'stop';
  current_power_w: number;
  target_power_w: number;
  savings_usd: number;
  revenue_impact_usd: number;
}

export interface CurtailmentConfig {
  price_threshold: number;
  max_throttle: number;
  require_confirm: boolean;
}

// Monitoring Alert Types
export interface AlertRule {
  id: string;
  name: string;
  condition: 'offline' | 'high_temp' | 'hashrate_drop' | 'fan_failure';
  threshold: number;
  duration_seconds: number;
}

export interface Alert {
  id: string;
  rule_id: string;
  miner_id: string;
  triggered_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  details: Record<string, any>;
}
